---
name: coding-cloudformation
description: CloudFormation - AWS-native IaC, a situational leaf of coding-shape-iac. Terraform is the default over CFN for new AWS work. Stub - fill later.
---

# coding-cloudformation

**Stub.** A situational leaf of `coding-shape-iac`. Fill with real conventions later.

CloudFormation is AWS-native IaC (YAML/JSON templates, managed stacks). It is not Kai's default - Terraform is the API-hitting leg of the trifecta and the default for new AWS work. Reach for CFN only when an existing stack already lives there, a service ships CFN-only, or a managed offering (SAM, CDK output, Service Catalog) requires it.

## To fill later

- When CFN is forced (existing stacks, CFN-only services, SAM/CDK).
- Stack vs StackSet, change sets, drift detection.
- How CFN coexists with the Terraform that owns the rest of the AWS surface.
- CDK note - if CDK shows up, decide whether it lives here or in its own skill.

## Triggers

cloudformation, cfn, aws cloudformation, sam, cdk, change set, stackset, aws-native iac.

## See also

- `coding-shape-iac` - the IaC umbrella.
- `coding-terraform` - the default over CloudFormation.
- `coding-aws` - the cloud CFN targets.
