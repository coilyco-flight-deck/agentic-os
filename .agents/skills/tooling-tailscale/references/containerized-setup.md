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
      - "127.0.0.1:1055:1055"             # SOCKS5, bound to Mac loopback only
    restart: unless-stopped
```

Inject the auth key without writing it to disk:

```bash
TS_AUTHKEY="$(ward ops aws ssm get-parameter \
  --name /coilysiren/mac-proxy/ts-authkey --with-decryption \
  --query 'Parameter.Value' --output text)" docker compose up -d
```

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
