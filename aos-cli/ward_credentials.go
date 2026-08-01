package main

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

const wardForgejoTokenParameter = "/forgejo/coilyco-ops/api-token"

type environmentLookup func(string) (string, bool)
type wardCredentialFetch func(context.Context) (string, error)

func wardLaunchEnvironment(ctx context.Context) ([]string, error) {
	return buildWardLaunchEnvironment(
		ctx,
		os.Environ(),
		os.LookupEnv,
		fetchWardForgejoToken,
	)
}

func buildWardLaunchEnvironment(
	ctx context.Context,
	environment []string,
	lookup environmentLookup,
	fetch wardCredentialFetch,
) ([]string, error) {
	token, err := resolveWardForgejoToken(ctx, lookup, fetch)
	if err != nil {
		return nil, err
	}
	return replaceEnvironment(environment, "FORGEJO_TOKEN", token), nil
}

func resolveWardForgejoToken(
	ctx context.Context,
	lookup environmentLookup,
	fetch wardCredentialFetch,
) (string, error) {
	if token, ok := lookup("FORGEJO_TOKEN"); ok && token != "" {
		return token, nil
	}
	token, err := fetch(ctx)
	if err != nil {
		return "", fmt.Errorf(
			"resolve Ward Forgejo broker credential from AOS deployment source: %w",
			err,
		)
	}
	token = strings.TrimRight(token, "\r\n")
	if token == "" || token == "None" {
		return "", fmt.Errorf(
			"resolve Ward Forgejo broker credential from AOS deployment source: empty value",
		)
	}
	return token, nil
}

func fetchWardForgejoToken(ctx context.Context) (string, error) {
	// This provider-specific read is the host Git helper's credential-bootstrap exception.
	// It stays in AOS because Ward needs the credential before exposing a guarded surface.
	awsPath, err := exec.LookPath("aws")
	if err != nil {
		return "", fmt.Errorf("find AWS CLI for credential bootstrap: %w", err)
	}
	command := exec.CommandContext(
		ctx,
		awsPath,
		"ssm",
		"get-parameter",
		"--name",
		wardForgejoTokenParameter,
		"--with-decryption",
		"--query",
		"Parameter.Value",
		"--output",
		"text",
	)
	command.Env = removeEnvironment(os.Environ(), "WARD_CONFIG_REF")
	var output bytes.Buffer
	command.Stdout = &output
	if err := command.Run(); err != nil {
		return "", fmt.Errorf(
			"read %s with the host AWS session: %w",
			wardForgejoTokenParameter,
			err,
		)
	}
	return output.String(), nil
}

func replaceEnvironment(environment []string, key, value string) []string {
	updated := removeEnvironment(environment, key)
	return append(updated, key+"="+value)
}

func removeEnvironment(environment []string, key string) []string {
	prefix := key + "="
	updated := make([]string, 0, len(environment))
	for _, entry := range environment {
		if strings.HasPrefix(entry, prefix) {
			continue
		}
		updated = append(updated, entry)
	}
	return updated
}
