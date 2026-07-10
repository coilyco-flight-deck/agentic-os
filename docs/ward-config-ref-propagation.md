# WARD_CONFIG_REF propagation

Shell entrypoints derive `AOS_REPO_ROOT` from the checkout that sourced them,
then `shell/common.sh` exports `WARD_CONFIG_REF` from that repo's current HEAD.
Child `warded` processes inherit the exported value, so a surface session does
not need an inline `WARD_CONFIG_REF=...` prefix for normal use.

The dev-base image keeps its build-time `WARD_CONFIG_REF_COMMIT` behavior. That
path is separate and still stamps the image against the commit that built it.

Manual inline overrides are for emergency diagnostics only.
