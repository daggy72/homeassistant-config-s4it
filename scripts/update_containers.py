#!/usr/bin/env python3
"""Weekly update of the Cassano HA + ESPHome containers (runs on the Mac Mini via launchd).

Per service: pull :stable; nothing new -> done. HA x.y.0 releases are skipped (wait for .1).
HA gets a check_config with the NEW image before the swap, and a health compare after it.
Any failure -> old image retagged as :stable and the container recreated (rollback).
Result -> log + HA persistent notification. Usage: update_containers.py [--dry-run]
"""
import json, subprocess, sys, time, urllib.request
from datetime import datetime

DRY = "--dry-run" in sys.argv
DOCKER = "sudo /usr/local/bin/docker"
COMPOSE = f"{DOCKER} compose -f /volume1/docker/homeassistant/docker-compose.yaml"
CONFIG = "/volume1/docker/homeassistant/homeassistant/config"
HA_IMG = "ghcr.io/home-assistant/home-assistant:stable"
ESP_IMG = "ghcr.io/esphome/esphome:stable"
CRED = json.load(open("/Users/dagmar/.claude/credentials/ha-claude.json"))


def log(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def nas(cmd, check=True):
    r = subprocess.run(["ssh", "nas-docker", cmd], capture_output=True, text=True, timeout=1800)
    if check and r.returncode:
        raise RuntimeError(f"{cmd.split()[2:4]} failed: {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout.strip()


def image_id(img):
    return nas(f"{DOCKER} image inspect -f '{{{{.Id}}}}' {img}")


def version(img):
    return nas(f"{DOCKER} image inspect -f '{{{{index .Config.Labels \"org.opencontainers.image.version\"}}}}' {img}")


def ha(path, data=None):
    req = urllib.request.Request(CRED["base_url"] + path, method="POST" if data else "GET",
                                 data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": "Bearer " + CRED["token"], "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20))


def health(entries=None):
    """(loaded config entries, unavailable entities) or None when HA does not answer."""
    try:
        config_entries = ha("/api/config/config_entries/entry")
        states = ha("/api/states")
    except Exception:
        return None
    if entries is not None:
        entries.clear()
        entries.update((e["entry_id"], e) for e in config_entries)
    return (sum(e["state"] == "loaded" for e in config_entries),
            sum(s["state"] == "unavailable" for s in states))


def wait_health(minutes, entries=None):
    for _ in range(minutes * 2):
        h = health(entries)
        if h:
            return h
        time.sleep(30)
    return None


def notify(title, msg):
    log(f"{title}: {msg}")
    if DRY:
        return
    for attempt in range(5):
        try:
            ha("/api/services/persistent_notification/create",
               {"title": title, "message": msg, "notification_id": "container_update"})
            return
        except Exception as e:
            if attempt == 4:
                log(f"notify failed: {e}")
            else:
                time.sleep(30)


def rollback(service, img, old_id):
    nas(f"{DOCKER} tag {old_id} {img} && {COMPOSE} up -d {service}")


def update(service, img, check):
    old_id = image_id(img)
    old_ver = version(img)
    nas(f"{DOCKER} tag {old_id} {img.replace(':stable', ':rollback')}")
    nas(f"{DOCKER} pull -q {img}")
    new_id, new_ver = image_id(img), version(img)
    if new_id == old_id:
        log(f"{service}: {old_ver} is current")
        return
    if service == "homeassistant" and new_ver.endswith(".0"):
        nas(f"{DOCKER} tag {old_id} {img}")
        log(f"{service}: {new_ver} skipped (x.y.0, wait for .1); stay on {old_ver}")
        return
    if DRY:
        nas(f"{DOCKER} tag {old_id} {img}")
        log(f"{service}: DRY RUN would update {old_ver} -> {new_ver}")
        return
    try:
        check(img, old_id)
    except Exception as e:
        rollback(service, img, old_id)
        wait_health(10)
        notify(f"{service} update rolled back", f"{old_ver} -> {new_ver} failed: {e}. Running {old_ver} again.")
        return
    notify(f"{service} updated", f"{old_ver} -> {new_ver}")


def check_ha(img, old_id):
    out = nas(f"{DOCKER} run --rm --network host -v {CONFIG}:/config --entrypoint python {img} "
              f"-m homeassistant --script check_config -c /config", check=False)
    if "Failed config" in out or "Invalid config" in out:
        raise RuntimeError("check_config: " + out[-300:])
    before_entries, after_entries = {}, {}
    before = health(before_entries)
    if not before:
        raise RuntimeError("HA not healthy before the update")
    nas(f"{COMPOSE} up -d homeassistant")
    time.sleep(60)
    after = wait_health(10, after_entries)
    time.sleep(180)  # let integrations finish loading
    after = health(after_entries) or after
    if not after:
        raise RuntimeError("HA API down 10 min after the update")
    if after[0] < before[0] or after[1] > before[1] + 5:
        lost = [f"{e['title']} ({e['domain']}: {after_entries.get(entry_id, {}).get('state', 'missing')})"
                for entry_id, e in before_entries.items()
                if e["state"] == "loaded" and after_entries.get(entry_id, {}).get("state") != "loaded"]
        raise RuntimeError(f"health worse: loaded {before[0]}->{after[0]}, unavailable {before[1]}->{after[1]}"
                           + ("; lost entries: " + ", ".join(lost) if lost else ""))


def check_esphome(img, old_id):
    nas(f"{COMPOSE} up -d esphome")
    for _ in range(20):
        time.sleep(15)
        if nas(f"{DOCKER} inspect -f '{{{{.State.Health.Status}}}}' HA_esphome") == "healthy":
            return
    raise RuntimeError("HA_esphome not healthy after 5 min")


if __name__ == "__main__":
    log(f"--- run {'(dry)' if DRY else ''}")
    for svc, img, chk in (("homeassistant", HA_IMG, check_ha), ("esphome", ESP_IMG, check_esphome)):
        try:
            update(svc, img, chk)
        except Exception as e:
            notify(f"{svc} update failed", str(e))
    # ponytail: device firmware (10 fancoil boards) and HACS components (VT) are not updated here.
