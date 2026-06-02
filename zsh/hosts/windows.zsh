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

# Stop msys/Git Bash rewriting leading-slash args into Windows paths before
# they reach native exes (mangles SSM names). See coilysiren/coily#156.
export MSYS_NO_PATHCONV=1
