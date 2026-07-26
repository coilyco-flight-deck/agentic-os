#!/usr/bin/env bash

set -euo pipefail

docker buildx build \
  --check \
  --build-arg WARD_CONFIG_REF_COMMIT=0000000000000000000000000000000000000000 \
  --build-context aos-cli=aos \
  --build-context aos-ward-specs=.ward \
  --build-context aosguard-spec=.specgen \
  --build-context aosguard-python=agentic_os \
  --target dev-base-full \
  --file docker/dev-base/Dockerfile \
  docker/dev-base
