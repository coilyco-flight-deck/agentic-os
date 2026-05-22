---
name: coding-azure
description: Azure umbrella skill. Multi-cloud experience from Textio (Azure OpenAI + BGP VPN to AWS). Reach for Azure when a job already runs there or when Azure OpenAI is specifically required. AWS is Kai's default cloud, GCP is secondary, Azure is third. Triggers - azure, az, microsoft azure, aks, azure storage, azure functions, azure openai, blob storage, cosmos db, azure devops, azure ad, entra, key vault.
---

# coding-azure

Umbrella for any Azure work.

## Defaults

- **Auth**: `az login` for local; service principals in CI.
- **CLI**: `az`. No coily wrapper.
- **Region**: project-pinned.
- **IaC**: Terraform (azurerm provider). Cross-link to [`coding-terraform`](../coding-terraform/SKILL.md).
- **Secrets**: Key Vault (analogous to AWS SSM SecureString).

## Posture vs AWS / GCP

Azure is third-priority for new infra. Reach for it when:
- Azure OpenAI is specifically needed (separate billing/governance from openai.com).
- An existing system already lives there.
- A multi-cloud requirement (BGP VPN, hybrid identity) actually warrants the surface.

## Past employer experience

- **Textio** - Azure OpenAI deployment, multi-cloud BGP VPN to AWS, customer-data pipelines.

## When this skill is active

Editing Azure-targeted code or infra. Inherit Kai's posture before reaching for generic Azure guidance.
