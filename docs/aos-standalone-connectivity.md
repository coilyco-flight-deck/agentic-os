---
doc_goal: Define MCP inventory and tailnet projection for standalone AOS launches.
---
# AOS standalone connectivity

AOS preserves the operator's MCP connectivity baseline when AOS owns the
container. This bootstrap behavior applies without `--warded` and does not
change the selected role's authority.

## MCP inventory

AOS discovers the resolved host `~/.mcporter/mcporter.json` when that file is
present. The launcher mounts only that inventory read-only. It does not mount
host HOME, OAuth caches, or unrelated harness configuration.

Container bootstrap runs `agent-compose mcp` after projecting harness defaults.
Claude and Codex receive native MCP registrations. Every harness receives the
mcporter inventory as an on-demand CLI fallback.

## Tailnet HTTP endpoints

AOS joins the shared `ward-tailnet` Docker network whenever that network
exists. It exports `AOS_TAILNET_SOCKS5=socks5h://tailscale-proxy:1055` for
tools that explicitly support SOCKS without setting a global proxy.

AOS also resolves each HTTP MCP hostname on the host. When an address is
inside a Tailscale range, AOS:

* rewrites that endpoint in the ephemeral inventory to a private loopback port
* starts an unprivileged TCP bridge for the endpoint
* sends bridge traffic through `tailscale-proxy:1055`

The bridge sends the resolved tailnet address to the SOCKS proxy, so it does
not depend on proxy-side MagicDNS. Public MCP endpoints keep their original
URLs and do not use the bridge.

Tailnet MCP bridging currently supports `http` URLs. AOS rejects a detected
tailnet `https` endpoint instead of silently breaking TLS hostname validation.

## Outage behavior

MCP registration remains visible when the standing proxy is cycling. Calls to
tailnet-only endpoints fail until infrastructure restores the proxy. A running
standalone agent can use the bridge after the proxy returns because each bridge
dials the proxy for every new connection.

The infrastructure tailscale-proxy role owns proxy convergence. AOS neither
starts nor repairs that service.

## Security and authority

The host inventory is operator configuration, not role policy. Projection adds
tool discovery and network reach only. `--role` still selects context,
`--composed` still selects agent-compose projection, and Ward remains the only
owner of Ward runtime policy when `--warded` is present.

## See also

* [AOS launch CLI](aos-cli.md) - launch flags and container contract.
* [Tooling Tailscale skill](../.agents/skills/tooling-tailscale/SKILL.md) - shared proxy and Docker network contract.
