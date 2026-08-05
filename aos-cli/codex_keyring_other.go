//go:build !darwin

package main

import "context"

func readCodexKeyring(context.Context, string, string) ([]byte, error) {
	return nil, errCodexKeyringUnsupported
}
