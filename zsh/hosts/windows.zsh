# Windows-specific PATH. zsh runs under Git Bash; paths are POSIX-style.

typeset -U path PATH
path=(
  "$HOME/bin"
  "$HOME/.local/bin"
  "$HOME/.cargo/bin"
  /c/Program\ Files/Git/bin
  /c/Program\ Files/Git/usr/bin
  $path
)
export PATH

# Stop msys/Git Bash from rewriting leading-slash args into Windows paths
# before they reach native exes. Without this, `coily ops aws ssm` mangles
# SSM names like /coilysiren/... into C:/.../coilysiren/..., surfacing as
# ParameterNotFound / ValidationException. See coilysiren/coily#156.
export MSYS_NO_PATHCONV=1
