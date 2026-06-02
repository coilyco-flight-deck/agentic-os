---
name: coding-terraform-module-library
description: Build reusable Terraform modules for AWS / Azure / GCP / OCI. Use when creating multi-cloud infrastructure modules or standardizing cloud provisioning.
---

# Terraform Module Library

Production-ready Terraform module patterns for AWS, Azure, GCP, and OCI infrastructure.

## Purpose

Create reusable, well-tested Terraform modules for common cloud infrastructure patterns across multiple cloud providers.

## When to Use

- Build reusable infrastructure components
- Standardize cloud resource provisioning
- Implement infrastructure as code best practices
- Create multi-cloud compatible modules
- Establish organizational Terraform standards

## Module Structure

- [module structure](references/module-structure.md) - library layout and the standard per-module file pattern.

## AWS VPC Module Example

- [AWS VPC example](references/aws-vpc-example.md) - full main.tf, variables.tf, and outputs.tf for a VPC module.

## Best Practices

1. **Use semantic versioning** for modules
2. **Document all variables** with descriptions
3. **Provide examples** in examples/ directory
4. **Use validation blocks** for input validation
5. **Output important attributes** for module composition
6. **Pin provider versions** in versions.tf
7. **Use locals** for computed values
8. **Implement conditional resources** with count/for_each
9. **Test modules** with Terratest
10. **Tag all resources** consistently

**Reference:** See `references/aws-modules.md` and `references/oci-modules.md`

## Module Composition and Testing

- [composition and testing](references/composition-and-testing.md) - composing VPC + RDS modules and a Terratest harness.

## Related Skills

- `multi-cloud-architecture` - For architectural decisions
- `cost-optimization` - For cost-effective designs
