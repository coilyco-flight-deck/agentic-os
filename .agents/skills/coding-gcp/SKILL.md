---
name: coding-gcp
description: GCP umbrella skill. Secondary cloud - reach for it when a job already runs there. AWS is Kai's default for new infra.
---

# coding-gcp

Umbrella for any GCP work.

## Defaults

- **Auth**: `gcloud auth application-default login` for local dev; service accounts in CI.
- **CLI**: `gcloud`, `gsutil`, `bq`. No ward wrapper yet (AWS has one because that's where the privileged surface is).
- **Region**: project-pinned, no default to guess.
- **IaC**: Terraform (Google provider). Cross-link to [`coding-terraform`](../coding-terraform/SKILL.md).
- **Secrets**: Secret Manager (analogous to AWS SSM SecureString).

## Posture vs AWS

GCP is reach-for-when-job-requires-it, not default. AWS is Kai's primary cloud (homelab, SSM-resident config, daily ops). When designing new infrastructure for personal projects, default AWS unless there's a specific GCP-only service in play (BigQuery, Vertex AI, Cloud Run for a thin proof-of-concept).

## Past employer experience

- **Bluelink** - Java/Python on GKE, GCP-primary infrastructure.

## Triggers

gcp, google cloud, gke, gcs, cloud run, cloud functions, bigquery, pubsub, firestore, cloud sql, vertex ai, gcloud, gsutil, dataflow, secret manager, iam.

## When this skill is active

Editing GCP-targeted code or infra. Inherit Kai's defaults before reaching for generic GCP guidance.
