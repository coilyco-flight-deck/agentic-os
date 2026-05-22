---
name: coding-shape-cloud
description: Category umbrella for cloud infrastructure work. Multi-cloud experience across AWS (primary), GCP (Bluelink/Kapwing), Azure (Textio). Cross-cloud patterns - region pinning, IAM-not-users, IaC over click-ops, secrets in cloud-native param stores. Triggers - cloud, public cloud, multi-cloud, hybrid cloud, iam, region, availability zone, vpc, peering, transit gateway, bgp vpn, cloud secrets, cloud parameter store, cloud iac, cloudformation, pulumi.
---

# coding-shape-cloud

Umbrella for any work that targets a public cloud. Cross-cuts AWS, GCP, Azure, and any other future provider.

## Per-cloud skills

- [`coding-aws`](../coding-aws/SKILL.md) - **primary** cloud. Homelab adjacent (SSM, Route53), default for new infra.
- [`coding-gcp`](../coding-gcp/SKILL.md) - **secondary**. Reach for when an existing job lives there or for GCP-only services (BigQuery, Vertex AI, Cloud Run for thin POCs).
- [`coding-azure`](../coding-azure/SKILL.md) - **tertiary**. Reach for when Azure OpenAI is specifically required, or when an existing system already lives there.

## Cross-cloud principles

- **One region pinned per project.** No "auto-pick by latency" cleverness. AWS default `us-east-1`, but document the choice in repo conventions.
- **IAM, not users.** Roles + policies, federated identity (SSO, workload identity). Long-lived access keys are an anti-pattern in any cloud.
- **IaC over click-ops.** Terraform first (cross-cloud surface). CloudFormation, Pulumi, ARM templates only when an existing project commits to them.
- **Secrets in the cloud-native param store.** AWS SSM SecureString, GCP Secret Manager, Azure Key Vault. Same shape, different door. Per the configs-in-SSM rule.
- **Tag everything.** Cost attribution, ownership, environment, lifecycle. Cloud bills get unrecoverable without tags.
- **Avoid vendor lock that doesn't transfer.** OTel-shaped instrumentation, S3-compatible storage interfaces, Kubernetes-shaped compute. Don't reach for a cloud-only primitive when a portable one exists, unless the cloud-only one is materially better for the use case.

## When to multi-cloud

Real reasons:
- Workload portability requirement from compliance/contract.
- A specific service that exists only on one provider (Azure OpenAI, BigQuery, AWS Lambda's particular runtime).
- Hybrid identity requirement (BGP VPN, federated AAD, etc).

Not real reasons:
- "Avoid vendor lock-in" as a vibe with no concrete trigger.
- Personal preference for a different UI.
- "What if AWS goes down" (your single-cloud uptime is way better than your multi-cloud operational complexity).

## Anti-patterns

- Manually-clicked resources hidden from IaC.
- Long-lived root account keys.
- Cross-cloud architectures with no documented why (just operational tax).
- Cloud-native primitives chosen for novelty, not fit (Lambdas where a long-running service was right, K8s where a Lambda was right).

## When this skill is active

Any cloud-targeted work, especially when it crosses providers or when the choice between providers is open.

## See also

- [`coding-terraform`](../coding-terraform/SKILL.md) - the IaC tool spanning all three.
- [`coding-kubernetes`](../coding-kubernetes/SKILL.md) - the portable compute layer.
- `agentic-os-kai/SSM.md` - the AWS-side parameter inventory.
