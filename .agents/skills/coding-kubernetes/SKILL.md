---
name: coding-kubernetes
description: Kubernetes umbrella skill. K3s on kai-server is the homelab cluster. kubectl via coily wrapper. Helm for packaged apps. Plain manifests over Kustomize.
---

# coding-kubernetes

Umbrella for any Kubernetes work.

## Triggers

kubernetes, k8s, k3s, kubectl, helm, manifest, deployment, statefulset, daemonset, configmap, secret, ingress, namespace, pod, service, pv, pvc, externalsecrets, cert-manager.

## Defaults

- **Cluster**: K3s on `kai-server` (homelab). Single-node by design. Tailscale-fronted.
- **kubectl**: route through `coily ops kubectl` (audit binding, context routing). See [`coily-ops-kubectl-meta`](../coily-ops-kubectl-meta/SKILL.md) and `coily-ops-kubectl-usage` for verbs.
- **Packaging**: Helm for upstream apps with charts. Plain YAML manifests for Kai's own services. Kustomize is fine when it earns its complexity, not by default.
- **Secrets**: ExternalSecrets operator + AWS SSM. No raw `Secret` resources committed to git, ever.
- **Ingress**: Traefik (k3s default).
- **Cert**: cert-manager + Route53 DNS-01 via [`/coilysiren/route53/zone-id`](../../../../agentic-os-kai/SSM.md).

## Conventions

- Manifests in [`coilysiren/infrastructure`](https://github.com/coilysiren/infrastructure). Apply via the repo's deploy scripts, not ad-hoc `kubectl apply`.
- Namespaces match the service name. One service, one namespace, when reasonable.
- Resource limits set explicitly (cluster is small, OOM evictions are real - see [`ops-investigation-k3s-pod-eviction`](../../../../agentic-os-kai/.agents/skills/ops-investigation-k3s-pod-eviction/SKILL.md)).

## Investigation playbooks

- Pod evictions → [`ops-investigation-k3s-pod-eviction`](../../../../agentic-os-kai/.agents/skills/ops-investigation-k3s-pod-eviction/SKILL.md).
- Cluster upgrades → [`ops-investigation-k3s-upgrade-homelab`](../../../../agentic-os-kai/.agents/skills/ops-investigation-k3s-upgrade-homelab/SKILL.md).

## When this skill is active

Editing manifests, debugging cluster state, designing a new k8s service. Inherit Kai's homelab posture before generic Kubernetes guidance.
