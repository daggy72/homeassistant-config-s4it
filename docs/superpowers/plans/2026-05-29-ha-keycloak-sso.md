# Home Assistant Keycloak SSO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure Home Assistant as a Keycloak-managed OIDC application that can be activated through the Keycloak management portal.

**Architecture:** Keycloak owns authentication and user activation. Home Assistant consumes OIDC through the `hass-oidc-auth` custom integration, reading app-specific Keycloak client roles from a dedicated `groups` claim. Native HA login remains available as fallback during rollout.

**Tech Stack:** Home Assistant YAML, `hass-oidc-auth`, Keycloak Admin REST API, S4IT Keycloak management portal.

---

## File Structure

- Modify: `homeassistant/config/configuration.yaml`
  - Adds the `auth_oidc` integration configuration.
- Create: `docs/superpowers/specs/2026-05-29-ha-keycloak-sso-design.md`
  - Records the approved design and rollout constraints.
- Create: `docs/superpowers/plans/2026-05-29-ha-keycloak-sso.md`
  - Records this implementation plan.

## Task 1: Prepare Home Assistant OIDC YAML

**Files:**
- Modify: `homeassistant/config/configuration.yaml`

- [x] **Step 1: Add `auth_oidc` after the `http` block**

```yaml
auth_oidc:
  client_id: homeassistant
  discovery_url: "https://keycloak.sales4.it/realms/sales4/.well-known/openid-configuration"
  display_name: "Sales4 SSO"
  groups_scope: homeassistant-roles
  roles:
    user: homeassistant-user
    admin: homeassistant-admin
  features:
    default_redirect: false
    force_https: true
```

- [x] **Step 2: Parse the YAML**

Run:

```bash
ruby -ryaml -e 'YAML.load_file("homeassistant/config/configuration.yaml"); puts "configuration.yaml parses"'
```

Expected: prints `configuration.yaml parses`.

- [x] **Step 3: Confirm the `auth_oidc` block exists**

Run:

```bash
rg -n "auth_oidc|client_id: homeassistant|homeassistant-roles|homeassistant-admin" homeassistant/config/configuration.yaml
```

Expected: each configured value is found once.

## Task 2: Create Keycloak Application

**Files:**
- No repository file changes. Use Keycloak Admin REST API with credentials from `/Users/dagmar/DEV-S4IT/keycloak-management/keycloak-mcp-extended/.env.dev`.

- [x] **Step 1: Create or update the public OIDC client**

Create client `homeassistant` in realm `sales4` with:

```json
{
  "clientId": "homeassistant",
  "name": "Home Assistant",
  "description": "Home Assistant CM1 OIDC login",
  "protocol": "openid-connect",
  "publicClient": true,
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false,
  "implicitFlowEnabled": false,
  "serviceAccountsEnabled": false,
  "redirectUris": ["https://hacm1.sales4.it/auth/oidc/callback"],
  "webOrigins": ["https://hacm1.sales4.it"],
  "attributes": {
    "pkce.code.challenge.method": "S256",
    "post.logout.redirect.uris": "https://hacm1.sales4.it/*"
  }
}
```

- [x] **Step 2: Create client roles**

Create missing roles on client `homeassistant`:

```text
homeassistant-user
homeassistant-admin
```

- [x] **Step 3: Create role claim client scope**

Create client scope `homeassistant-roles` if missing:

```json
{
  "name": "homeassistant-roles",
  "description": "Expose Home Assistant client roles as groups for HA OIDC auth",
  "protocol": "openid-connect"
}
```

- [x] **Step 4: Create protocol mapper**

Create or update mapper `homeassistant-client-roles` on client scope `homeassistant-roles`:

```json
{
  "name": "homeassistant-client-roles",
  "protocol": "openid-connect",
  "protocolMapper": "oidc-usermodel-client-role-mapper",
  "config": {
    "usermodel.clientRoleMapping.clientId": "homeassistant",
    "claim.name": "groups",
    "jsonType.label": "String",
    "multivalued": "true",
    "id.token.claim": "true",
    "access.token.claim": "true",
    "userinfo.token.claim": "true",
    "introspection.token.claim": "true",
    "lightweight.claim": "false"
  }
}
```

- [x] **Step 5: Assign the client scope**

Assign `homeassistant-roles` as a default client scope on client `homeassistant`.

- [x] **Step 6: Assign initial admin access**

Assign `homeassistant-admin` to Keycloak user `dagmar`.

- [x] **Step 7: Verify Keycloak state**

Fetch and print:

```text
clientId=homeassistant
redirectUris=https://hacm1.sales4.it/auth/oidc/callback
webOrigins=https://hacm1.sales4.it
roles=homeassistant-admin,homeassistant-user
defaultClientScopes includes homeassistant-roles
mapper claim.name=groups
dagmar has homeassistant-admin
```

## Task 3: Final Verification

**Files:**
- Read only, no new file changes.

- [x] **Step 1: Inspect repository diff**

Run:

```bash
git diff -- homeassistant/config/configuration.yaml docs/superpowers/specs/2026-05-29-ha-keycloak-sso-design.md docs/superpowers/plans/2026-05-29-ha-keycloak-sso.md
```

Expected: only the OIDC config and docs are changed.

- [x] **Step 2: Run available tests**

Run:

```bash
python3 -m pytest tests -q
```

Expected: pass when `pytest` is installed. If `pytest` is unavailable in the local shell, record that limitation and rely on YAML parsing plus NAS HA config check after HACS installation.

- [x] **Step 3: Commit changes**

Run:

```bash
git add homeassistant/config/configuration.yaml docs/superpowers/specs/2026-05-29-ha-keycloak-sso-design.md docs/superpowers/plans/2026-05-29-ha-keycloak-sso.md
git commit -m "feat: add Home Assistant Keycloak SSO config"
```

Expected: commit created on branch `feature/ha-keycloak-sso`.
