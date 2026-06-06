---
name: coding-pulumi
description: Pulumi - code-first IaC (real languages instead of HCL), a situational leaf of coding-shape-iac. Reach for it only when a project already commits to it. Stub - fill later.
---

# coding-pulumi

**Stub.** A situational leaf of [`coding-shape-iac`](../coding-shape-iac/SKILL.md). Fill with real conventions when a Pulumi project lands.

Pulumi expresses infrastructure in general-purpose languages (Python, TypeScript, Go) instead of HCL. It is not Kai's default - Terraform is the API-hitting leg of the trifecta. Reach for Pulumi only when an existing project already commits to it, or when programmatic infra logic genuinely needs a real language.

## To fill later

- State backend choice (Pulumi Cloud vs self-managed S3) and the secrets-in-SSM equivalent.
- Language default (Python, matching the rest of the stack).
- The plan-before-apply discipline (`pulumi preview` before `pulumi up`).
- When Pulumi over Terraform, and how to keep them from overlapping.

## Triggers

pulumi, pulumi up, pulumi preview, pulumi stack, code-first iac.

## See also

- [`coding-shape-iac`](../coding-shape-iac/SKILL.md) - the IaC umbrella.
- [`coding-terraform`](../coding-terraform/SKILL.md) - the default over Pulumi for new work.
