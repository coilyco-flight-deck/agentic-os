# Sourced first. Identity, editor, AWS defaults, coily lockdown root.
# Cross-platform; per-host PATH lives in hosts/<os>.zsh.

# History
HISTFILE=$HOME/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
setopt SHARE_HISTORY HIST_IGNORE_ALL_DUPS HIST_REDUCE_BLANKS HIST_VERIFY INTERACTIVE_COMMENTS

export LANG=en_US.UTF-8
export EDITOR=code
export GIT_EDITOR=nano
export SSH_KEY_PATH="$HOME/.ssh/id_rsa"
export CLI_MFA=ykman

export AWS_PROFILE=default
export AWS_REGION=us-east-1
export AWS_PAGER=""
export BAT_PAGER=""

export COILY_LOCKDOWN_ROOT="$HOME/projects/coilysiren"
