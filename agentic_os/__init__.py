"""Cross-repo pre-commit hooks and operating utilities for coilysiren/* repos.

Entry points are in pyproject.toml [project.scripts], hook declarations in
.pre-commit-hooks.yaml. The TLS trust-store fallback lives here because this is
the one file the aosguard guardfile bundle always ships, and a bundled module
runs with no package around it. Survey and the two properties to preserve when
editing it: .agents/skills/tooling-aosguard/references/tls-trust-store.md
"""
from __future__ import annotations

import functools
import ssl
import sys
from pathlib import Path

# macOS, Debian/Ubuntu, RHEL/Fedora, SUSE/Alpine, then the two Homebrew roots.
# Order is most-specific-first; the first readable bundle wins.
CA_BUNDLE_CANDIDATES = (
    "/etc/ssl/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/ca-bundle.pem",
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/usr/local/etc/ca-certificates/cert.pem",
)


def build_ssl_context(
    candidates: tuple[str, ...] = CA_BUNDLE_CANDIDATES,
) -> ssl.SSLContext:
    """A verifying context, repaired from disk when the interpreter has none.

    Verification is never weakened: an unrepairable context is returned as-is
    so the call still fails closed, and `trust_diagnosis` explains why.
    """
    context = ssl.create_default_context()
    if context.get_ca_certs():
        return context
    for candidate in candidates:
        try:
            context.load_verify_locations(cafile=candidate)
        except OSError:
            continue
        if context.get_ca_certs():
            return context
    return context


@functools.lru_cache(maxsize=1)
def shared_ssl_context() -> ssl.SSLContext:
    """Process-wide context, since loading a bundle costs real work."""
    return build_ssl_context()


def trust_diagnosis(context: ssl.SSLContext | None = None) -> str | None:
    """Why a TLS failure is local, or None when the trust store is fine.

    Call sites append this to their own error text, so a certificate failure
    stops reading as a bad endpoint or a stale token.
    """
    context = shared_ssl_context() if context is None else context
    if context.get_ca_certs():
        return None
    return (
        f"{sys.executable} has an empty CA trust store and no system bundle "
        f"was found at any of {len(CA_BUNDLE_CANDIDATES)} known paths. This is "
        f"a local trust problem, not a bad endpoint or credential. Run the "
        f"python.org 'Install Certificates.command' for this interpreter, or "
        f"point SSL_CERT_FILE at a bundle."
    )


def found_ca_bundle(
    candidates: tuple[str, ...] = CA_BUNDLE_CANDIDATES,
) -> str | None:
    """The bundle the fallback would load, for diagnostics and tests."""
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None
