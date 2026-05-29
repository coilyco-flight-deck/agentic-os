---
name: tooling-tailscale
description: Run Tailscale alongside a second host VPN by containerizing it - userspace/SOCKS5 mode in Docker so SSH and tailnet reach coexist with a WireGuard-based commercial VPN. Use when two VPNs fight over the macOS route table, or wiring Tailscale SSH to a peer behind a host VPN. Triggers - tailscale, tailnet, vpn coexistence, tailscale ssh, two vpns, wireguard utun conflict.
---

# Tailscale

## The host-route conflict

Tailscale and a second WireGuard-based VPN (any commercial WireGuard client - Mullvad, Proton, and similar) cannot coexist natively on one macOS host. Both install a WireGuard-shaped `utun` interface and a default-route override, and macOS has no native arbitration. Whichever toggles last wins and the other silently breaks - no tailnet routing, no public egress, or DNS resolving through the wrong resolver and returning NXDOMAIN. The business-tier products show the same shape because they ship the same WireGuard data plane underneath.

**Do not relitigate without new evidence.** Workarounds that did NOT work: pinning the route metric, manually adding scoped routes, running one at a time and toggling on demand (state survives toggles), Tailscale exit-node mode. The native answer is one VPN per host.

## The escape hatch: containerize Tailscale

Docker on macOS runs inside a Linux VM, so a containerized Tailscale builds its interface and routes inside the container's network namespace, never the host route table. The host VPN keeps the macOS default route uncontested. This still honors "one VPN per host" - the Mac has exactly one touching its routing table - while giving you tailnet reach.

Use userspace mode, not TUN: no `/dev/net/tun`, no `NET_ADMIN`, no route. Tailscale exposes a SOCKS5 proxy and you route specific connections through it.

### compose

```yaml
services:
  tailscale:
    image: tailscale/tailscale:latest
    hostname: mac-proxy                     # becomes the tailnet node name
    environment:
      TS_AUTHKEY: ${TS_AUTHKEY}            # reusable + ephemeral key, tag:proxy, minted by terraform/tailscale
      TS_USERSPACE: "true"
      TS_SOCKS5_SERVER: 0.0.0.0:1055
    ports:
      - "127.0.0.1:1055:1055"             # SOCKS5, bound to Mac loopback only
    restart: unless-stopped
```

Inject the auth key without writing it to disk:

```bash
TS_AUTHKEY="$(coily ops aws ssm get-parameter \
  --name /coilysiren/mac-proxy/ts-authkey --with-decryption \
  --query 'Parameter.Value' --output text)" docker compose up -d
```

### SSH through the proxy

```
# ~/.ssh/config
Host kai-server-proxied
  HostName <RESOLVED_TAILNET_IP>
  User kai
  ProxyCommand nc -X 5 -x 127.0.0.1:1055 %h %p
```

Resolve the peer IP at runtime rather than hardcoding it:

```bash
coily ops aws ssm get-parameter --name /coilysiren/kai-server/tailnet-ip \
  --with-decryption --query 'Parameter.Value' --output text
```

`ssh kai-server-proxied` now flows ssh -> SOCKS5 (container) -> tailscale userspace -> tailnet -> peer. The macOS route table is never touched, so the host VPN keeps full control of public egress.

## Sharp edges

- **Tailnet identity shifts.** The container is its own tailnet node, not the laptop, so give it a dedicated `tag:proxy` scoped to exactly its job. In the ACL: an `acls` rule `tag:proxy -> tag:server:22`, an `ssh` rule `tag:proxy -> tag:server`, and `tag:proxy` in `tagOwners` (empty owner list means only the admin OAuth mints it). The proxy then reaches kai-server over SSH and nothing else on the tailnet. Reusing `tag:physical` also works with no ACL edit, but it carries universal outbound - more than a SSH proxy needs.
- **Skip MagicDNS.** Dial the peer by tailnet IP (resolved from SSM above) instead of pushing DNS through the SOCKS proxy. Avoids a whole class of resolver confusion.
- **Mint a dedicated key in IaC, not by hand.** Devices, tags, and ACLs are Terraform-managed in `coilysiren/infrastructure` under `terraform/tailscale/`. Add a standalone `tailscale_tailnet_key` (reusable + ephemeral) tagged `tag:proxy` and stash it to `/coilysiren/mac-proxy/ts-authkey`. Make it `depends_on` the ACL resource so the new tag registers before the key mints. Do NOT copy the `services.yaml` sidecar pattern - those keys are non-reusable, non-ephemeral, tagged `tag:k8s`, and consumed once via ExternalSecret, none of which fits a recreatable local container.
- **Per-connection, not host-wide.** Only what you route through `:1055` reaches the tailnet. Fine for SSH to one peer. Other tailnet services (k3s, etc.) each need their own proxy route. This is not a drop-in replacement for full-tunnel Tailscale.
- **Userspace throughput is lower** than kernel TUN. Irrelevant for interactive SSH, matters if you pipe bulk data through the tunnel.

## Why this is here

A real conflict - Tailscale and a host VPN both grabbing the macOS route table - burned several debugging sessions, and the native-coexistence answer turned out to be "you can't." The containerized namespace is the only stable escape hatch found. Recorded here so the finding and the working setup are not re-derived under pressure the next time both VPNs need to run on one host.

## See also

- Official image: `https://hub.docker.com/r/tailscale/tailscale`, env-var reference at `https://tailscale.com/kb/1282/docker`.
- SSM params: `/coilysiren/mac-proxy/ts-authkey` (minted by `terraform/tailscale`), `/coilysiren/kai-server/tailnet-ip`. Inventory in `<personal-os-repo>/SSM.md`.
