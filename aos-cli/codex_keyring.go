package main

import "errors"

const codexDirectKeyringService = "Codex Auth"

var (
	errCodexKeyringNotFound    = errors.New("Codex keyring credential not found")
	errCodexKeyringUnsupported = errors.New("Codex keyring is unsupported")
)
