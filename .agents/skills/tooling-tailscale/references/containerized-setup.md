# Containerized Tailscale setup

Docker on macOS runs inside a Linux VM, so a containerized Tailscale builds its interface and routes inside the container's network namespace, never the host route table. The host VPN keeps the macOS default route uncontested. This still honors "one VPN per host" - the Mac has exactly one touching its routing table - while giving you tailnet reach.

Use userspace mode, not TUN: no `/dev/net/tun`, no `NET_ADMIN`, no route. Tailscale exposes a SOCKS5 proxy and you route specific connections through it.

## compose

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
      - "127.0.0.1:1055:1055"             # SOCKS5, published to Mac loopback only
    restart: unless-stopped
    networks: [ward-tailnet]               # in-VM consumers reach the box by name here
networks:
  ward-tailnet:
    name: ward-tailnet                     # fixed docker name - shared contract, do not rename
```

This is the standing, shared box. It runs once with `restart: unless-stopped`, and the infra sibling (the `mac-proxy` ansible role in `coilyco-flight-deck/infrastructure`) converges it, not ward. The compose lives at `ansible/roles/mac-proxy/files/compose.yaml` and is the authoritative copy - this block mirrors it.

Inject the auth key without writing it to disk:

```bash
TS_AUTHKEY="$(ward ops aws ssm get-parameter \
  --name /coilysiren/mac-proxy/ts-authkey --with-decryption \
  --query 'Parameter.Value' --output text)" docker compose up -d
```

## Two consumers, one box

The standing box serves SOCKS5 on `0.0.0.0:1055` to two distinct callers, and the compose above wires both:

- **Mac-host tools** reach it on the published `127.0.0.1:1055` loopback. SSH and any host-side client point at that port (see below). The bind stays loopback-only, so nothing off the Mac can dial it.
- **In-VM containers** that join the `ward-tailnet` network reach it by name as `socks5h://mac-proxy:1055`. The fixed docker name is what lets a `ward agent` carry resolve the box without an IP or SSM lookup. `socks5h` (not `socks5`) hands the hostname to tailscaled to resolve tailnet-side, which is what makes by-name dialing of tailnet peers work from inside the carry.

The second consumer is the carry side of `ward agent --ts-sidecar`. ward never converges this box - it only attaches a carry to `ward-tailnet` and preflights that `mac-proxy` is present. The two shared names, the `ward-tailnet` network and the `mac-proxy` host, are a contract between this compose and ward. See ward's [`docs/agent-ts-sidecar.md`](https://github.com/coilyco-flight-deck/ward/blob/main/docs/agent-ts-sidecar.md) for the carry-side attach, preflight, and by-name route.

## SSH through the proxy

```
# ~/.ssh/config
Host kai-server-proxied
  HostName <RESOLVED_TAILNET_IP>
  User kai
  ProxyCommand nc -X 5 -x 127.0.0.1:1055 %h %p
```

Resolve the peer IP at runtime rather than hardcoding it:

```bash
ward ops aws ssm get-parameter --name /coilysiren/kai-server/tailnet-ip \
  --with-decryption --query 'Parameter.Value' --output text
```

`ssh kai-server-proxied` now flows ssh -> SOCKS5 (container) -> tailscale userspace -> tailnet -> peer. The macOS route table is never touched, so the host VPN keeps full control of public egress.
