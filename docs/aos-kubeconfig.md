---
doc_goal: Define role-gated host kubeconfig projection for standalone AOS containers.
---
# AOS kubeconfig projection

AOS can project one operator-selected host kubeconfig into the full compatibility
container when AOS owns the standalone runtime:

```bash
aos \
  --agent codex \
  --role ops \
  --composed \
  --kubeconfig "/operator configs/homelab.yaml"
```

There is no default host path. The operator must select the source explicitly.
AOS resolves the path, requires a readable regular file, and verifies that it is
a single structurally valid Kubernetes `v1` `Config` document before Docker
starts.

## Role boundary

Standalone `director` and `ops` roles may receive the selected kubeconfig.
Other roles cause no source inspection, mount, or `KUBECONFIG` environment
projection. In particular, sealed `engineer` and `qa` launches receive no live
cluster credentials even when a source was supplied.

This allowlist belongs to the standalone AOS runtime. It does not transfer a
permission into Ward, agent-compose, or AOSguard merely because those layers
use the same role slug.

`--kubeconfig` is rejected with `--warded`. Ward owns warded runtime mounts, so
AOS does not pass an operator-local host path across that lifecycle boundary.

## Container projection

AOS passes the selected path to Docker as one bind-mount argument, so host paths
containing spaces remain intact. The file mounts read-only at:

```text
/run/aos/kubeconfig
```

The child process receives:

```text
KUBECONFIG=/run/aos/kubeconfig
```

The mount exposes the selected document and nothing else from the host
Kubernetes configuration directory.

## Binary, credentials, and transport

The full dev-base image ships the `kubectl` client binary. A binary in an
image is not live cluster access. Access exists only when container bring-up
also supplies all of the following:

* an authorized standalone role
* an explicitly selected kubeconfig
* network transport that can reach the kubeconfig's cluster endpoint

Private-network composition remains independent. AOS can attach the container
to `ward-tailnet` and expose `AOS_TAILNET_SOCKS5` alongside the kubeconfig
mount. The kubeconfig or invoked client still has to select the appropriate
proxy or otherwise use a reachable endpoint. Kubeconfig projection neither
starts nor repairs private-network infrastructure.

## See also

* [AOS launch CLI](aos-cli.md)
* [Standalone connectivity](aos-standalone-connectivity.md)
* [dev-base image](dev-base-image.md)
