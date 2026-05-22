---
name: coding-gcp
description: GCP umbrella skill. Multi-cloud experience from Bluelink (GCP-primary, K8s on GKE) and Kapwing (Python/NodeJS on GCP). Reach for GCP when a job already runs there, not as default for new infra (AWS is Kai's default). Triggers - gcp, google cloud, gke, gcs, cloud run, cloud functions, bigquery, pubsub, firestore, cloud sql, vertex ai, gcloud, gsutil, dataflow, secret manager, iam.
---

# coding-gcp

Umbrella for any GCP work.

## Defaults

- **Auth**: `gcloud auth application-default login` for local dev; service accounts in CI.
- **CLI**: `gcloud`, `gsutil`, `bq`. No coily wrapper yet (AWS has one because that's where the privileged surface is).
- **Region**: project-pinned, no default to guess.
- **IaC**: Terraform (Google provider). Cross-link to [`coding-terraform`](../coding-terraform/SKILL.md).
- **Secrets**: Secret Manager (analogous to AWS SSM SecureString).

## Posture vs AWS

GCP is reach-for-when-job-requires-it, not default. AWS is Kai's primary cloud (homelab, SSM-resident config, daily ops). When designing new infrastructure for personal projects, default AWS unless there's a specific GCP-only service in play (BigQuery, Vertex AI, Cloud Run for a thin proof-of-concept).

## Past employer experience

- **Kapwing** - Python/NodeJS on GCP, K8s, New Relic-monitored.
- **Bluelink** - Java/Python on GKE, GCP-primary infrastructure.

## When this skill is active

Editing GCP-targeted code or infra. Inherit Kai's defaults before reaching for generic GCP guidance.
