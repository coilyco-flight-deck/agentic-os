---
name: coding-kubernetes
description: Kubernetes umbrella skill. K3s on kai-server is the homelab cluster. kubectl via ward wrapper. Helm for packaged apps. Plain manifests over Kustomize.
low-context: required
---

# coding-kubernetes

Umbrella for any Kubernetes work.

## Triggers

kubernetes, k8s, k3s, kubectl, helm, manifest, deployment, statefulset, daemonset, configmap, secret, ingress, namespace, pod, service, pv, pvc, externalsecrets, cert-manager.

## Defaults

- **Cluster**: K3s on `kai-server` (homelab). Single-node by design. Tailscale-fronted.
- **kubectl**: route through `ward ops kubectl` (audit binding, context routing). See `ward-ops-kubectl-meta` (in ward) and `ward-ops-kubectl-usage` for verbs.
- **Packaging**: Helm for upstream apps with charts. Plain YAML manifests for Kai's own services. Kustomize is fine when it earns its complexity, not by default.
- **Secrets**: ExternalSecrets operator + AWS SSM. No raw `Secret` resources committed to git, ever.
- **Ingress**: Traefik (k3s default).
- **Cert**: cert-manager + Route53 DNS-01 via `/coilysiren/route53/zone-id` (see `SSM.md` in agentic-os-kai).

## Conventions

- Manifests in [`coilyco-flight-deck/infrastructure`](https://github.com/coilyco-flight-deck/infrastructure). Apply via the repo's deploy scripts, not ad-hoc `kubectl apply`.
- Namespaces match the service name. One service, one namespace, when reasonable.
- Resource limits set explicitly (cluster is small, OOM evictions are real - see `ops-investigation-k3s-pod-eviction` (in agentic-os-kai)).

## Investigation playbooks

- Pod evictions → `ops-investigation-k3s-pod-eviction` (in agentic-os-kai).
- Cluster upgrades → `ops-investigation-k3s-upgrade-homelab` (in agentic-os-kai).

## When this skill is active

Editing manifests, debugging cluster state, designing a new k8s service. Inherit Kai's homelab posture before generic Kubernetes guidance.
