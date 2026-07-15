ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS dev-base-lang-dotnet
ARG DOTNET_VERSION=10.0.301

# .NET SDK, pinned. dev-base shipped no C# toolchain, so any repo
# with C# to compile (eco-app's Eco mods, `dotnet build mods/*`) had to hand-install
# the SDK mid-run - the same absent-toolchain class as the uv/Python fix. Bake
# it in with Microsoft's official dotnet-install.sh at the exact pinned SDK version so
# `dotnet build` just works, no per-run install. --no-path since ENV owns DOTNET_ROOT
# and PATH; chmod a+rX so any run-as-uid runs it like every other tool here.
# Globalization: full ICU (libicu74 in the base apt block above), NOT invariant mode,
# so C# culture/string behaviour matches a normal host - no DOTNET_SYSTEM_GLOBALIZATION_INVARIANT.
RUN set -eux; \
    . /tmp/arch.env; \
    for attempt in 1 2 3; do \
      if curl -fsSL --retry 5 --retry-all-errors --retry-delay 5 \
        --connect-timeout 20 https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh \
        -o /tmp/dotnet-install.sh; then \
        break; \
      fi; \
      if [ "$attempt" -eq 3 ]; then \
        exit 1; \
      fi; \
      echo "dotnet-install.sh download attempt ${attempt} failed; retrying in 5s" >&2; \
      sleep 5; \
    done; \
    chmod 0755 /tmp/dotnet-install.sh; \
    for attempt in 1 2 3; do \
      if /tmp/dotnet-install.sh --version "${DOTNET_VERSION}" --architecture "${DOTNET_ARCH}" \
        --install-dir /usr/local/dotnet --no-path; then \
        break; \
      fi; \
      if [ "$attempt" -eq 3 ]; then \
        exit 1; \
      fi; \
      echo "dotnet install attempt ${attempt} failed; retrying in 5s" >&2; \
      sleep 5; \
    done; \
    rm /tmp/dotnet-install.sh; \
    chmod -R a+rX /usr/local/dotnet; \
    dotnet --version; dotnet --list-sdks
