---
name: coding-aws
description: AWS umbrella skill. Kai's primary cloud. Python via boto3, secrets and config via SSM Parameter Store, region pinned to us-east-1. Triggers - aws, amazon web services, boto3, botocore, awscli, aws-cli, ec2, s3, iam, lambda, ssm, parameter store, route53, cloudwatch, cloudfront, dynamodb, sqs, sns, eventbridge, rds, secrets manager, sts.
---

# coding-aws

Umbrella for any AWS work.

## Defaults

- **Region**: `us-east-1`. Pinned in `~/.aws/config` under `[default]` (NOT `[profile default]`). Region trap explained in [`SSM.md`](../../../../agentic-os-kai/SSM.md).
- **Auth**: AWS SSO via the default profile. Refresh with `aws sso login` when expired.
- **Python SDK**: `boto3`. Async via `aioboto3` only when concurrency is load-bearing.
- **Secrets and config**: SSM Parameter Store, SecureString. Never hardcode opaque ids. See the configs-in-SSM rule in `agentic-os-kai/AGENTS.md`.
- **CLI**: `coily ops aws ...` for privileged ops (audit-log binding, scope routing). Bare `aws ...` for read-only locals.

## Conventions

- Parameter naming: vendor-scoped, kebab-case leaf, SecureString. `/<vendor>/<key>` (e.g. `/elevenlabs/api-key`, `/coily/discord-webhook-url`).
- Region in code: read `AWS_REGION` env var, fall back to `us-east-1`. Don't hardcode in business logic.
- IAM: prefer policies + roles over users. Inline policies for one-off, managed policies for shared.

## When this skill is active

Anything that touches AWS APIs, configs, infrastructure, or the CLI. Inherit Kai's defaults before reaching for AWS conventions from training data.

## See also

- `agentic-os-kai/SSM.md` - parameter inventory.
- `coily-ops-aws-meta` - coily wrapper rules.
- `coding-terraform` - IaC umbrella for AWS infrastructure.
