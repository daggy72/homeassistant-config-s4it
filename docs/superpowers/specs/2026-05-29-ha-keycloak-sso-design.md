# Home Assistant Keycloak SSO Design

## Goal

Expose Home Assistant as a Keycloak-managed SSO application so users can be activated from the Keycloak management portal.

## Approach

Use the `christiaangoossens/hass-oidc-auth` Home Assistant custom integration instead of a reverse-proxy auth bridge. The integration gives Home Assistant a direct OIDC auth provider with callback URL `https://hacm1.sales4.it/auth/oidc/callback`.

Home Assistant will use a public Keycloak OIDC client with PKCE. This avoids storing a client secret in `secrets.yaml` and matches the integration's recommended default for this use case.

## Keycloak Shape

- Realm: `sales4`
- Client ID: `homeassistant`
- Client name: `Home Assistant`
- Redirect URI: `https://hacm1.sales4.it/auth/oidc/callback`
- Web origin: `https://hacm1.sales4.it`
- Post-logout redirect URI: `https://hacm1.sales4.it/*`
- Roles:
  - `homeassistant-user`
  - `homeassistant-admin`

The Keycloak management portal exposes non-internal OIDC clients and their client roles. Creating these roles on the `homeassistant` client makes Home Assistant appear as an application in the portal.

## Role Claim Mapping

The `hass-oidc-auth` integration maps HA permissions from a list claim, normally `groups`. The S4IT portal manages per-application client roles, not Keycloak groups, so Keycloak needs a dedicated client scope:

- Client scope: `homeassistant-roles`
- Protocol mapper: user client role mapper
- Source client: `homeassistant`
- Token claim: `groups`
- Included in: ID token, access token, userinfo

Home Assistant will request scope `homeassistant-roles`, then read the resulting `groups` claim.

## Home Assistant Configuration

`homeassistant/config/configuration.yaml` will add:

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

Native Home Assistant login remains available as the fallback. Do not enable automatic user linking during the first rollout because it can link an OIDC identity to an existing HA account solely by username.

## Deployment Order

1. Create and verify the Keycloak client, roles, scope, mapper, and role assignment.
2. Install the latest `hass-oidc-auth` release through HACS on the production HA instance.
3. Pull this config change on the Synology HA config checkout.
4. Restart Home Assistant.
5. Test SSO with a Keycloak user assigned `homeassistant-admin`.
6. Activate additional users from the Keycloak management portal.

## Verification

- Keycloak admin API confirms client `homeassistant` exists.
- Keycloak admin API confirms roles `homeassistant-user` and `homeassistant-admin` exist.
- Keycloak admin API confirms client scope `homeassistant-roles` is assigned to the client.
- Keycloak admin API confirms mapper emits `homeassistant` client roles into claim `groups`.
- Repository YAML parses successfully.
- Home Assistant config check should be run on the NAS after HACS installation because `custom_components/` is runtime-managed and gitignored.
