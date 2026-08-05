//go:build darwin

package main

import (
	"bytes"
	"context"
	"errors"
	"os/exec"
)

func readCodexKeyring(ctx context.Context, service, account string) ([]byte, error) {
	command := exec.CommandContext(
		ctx,
		"/usr/bin/security",
		"find-generic-password",
		"-s", service,
		"-a", account,
		"-w",
	)
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	if err := command.Run(); err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) &&
			(bytes.Contains(stderr.Bytes(), []byte("-25300")) ||
				bytes.Contains(stderr.Bytes(), []byte("could not be found"))) {
			return nil, errCodexKeyringNotFound
		}
		return nil, err
	}
	return bytes.TrimSpace(stdout.Bytes()), nil
}
