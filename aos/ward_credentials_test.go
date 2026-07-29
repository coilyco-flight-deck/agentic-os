package main

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestResolveWardForgejoTokenUsesAmbientOverride(t *testing.T) {
	t.Parallel()
	fetchCalled := false
	token, err := resolveWardForgejoToken(
		context.Background(),
		func(key string) (string, bool) {
			if key != "FORGEJO_TOKEN" {
				t.Fatalf("lookup key = %q", key)
			}
			return "ambient-token", true
		},
		func(context.Context) (string, error) {
			fetchCalled = true
			return "", errors.New("must not fetch")
		},
	)
	if err != nil {
		t.Fatal(err)
	}
	if token != "ambient-token" {
		t.Fatalf("token = %q", token)
	}
	if fetchCalled {
		t.Fatal("ambient token still fetched the deployment credential")
	}
}

func TestResolveWardForgejoTokenFetchesDeploymentCredential(t *testing.T) {
	t.Parallel()
	token, err := resolveWardForgejoToken(
		context.Background(),
		func(string) (string, bool) { return "", false },
		func(context.Context) (string, error) {
			return "broker-token\n", nil
		},
	)
	if err != nil {
		t.Fatal(err)
	}
	if token != "broker-token" {
		t.Fatalf("token = %q", token)
	}
}

func TestResolveWardForgejoTokenFailsClosed(t *testing.T) {
	t.Parallel()
	secret := "must-not-appear"
	_, err := resolveWardForgejoToken(
		context.Background(),
		func(string) (string, bool) { return "", false },
		func(context.Context) (string, error) {
			return secret, errors.New("host AWS session unavailable")
		},
	)
	if err == nil {
		t.Fatal("missing deployment credential succeeded")
	}
	if !strings.Contains(err.Error(), "host AWS session unavailable") {
		t.Fatalf("error = %q", err)
	}
	if strings.Contains(err.Error(), secret) {
		t.Fatalf("error exposed fetched output: %q", err)
	}
}

func TestResolveWardForgejoTokenRejectsEmptyValues(t *testing.T) {
	t.Parallel()
	for _, value := range []string{"", "\n", "None\n"} {
		value := value
		t.Run(value, func(t *testing.T) {
			t.Parallel()
			_, err := resolveWardForgejoToken(
				context.Background(),
				func(string) (string, bool) { return "", false },
				func(context.Context) (string, error) { return value, nil },
			)
			if err == nil || !strings.Contains(err.Error(), "empty value") {
				t.Fatalf("error = %v", err)
			}
		})
	}
}

func TestBuildWardLaunchEnvironmentProvidesOnlyCurrentToken(t *testing.T) {
	t.Parallel()
	environment, err := buildWardLaunchEnvironment(
		context.Background(),
		[]string{"PATH=/bin", "FORGEJO_TOKEN=stale"},
		func(string) (string, bool) { return "", false },
		func(context.Context) (string, error) { return "current\n", nil },
	)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"PATH=/bin", "FORGEJO_TOKEN=current"}
	if strings.Join(environment, "\n") != strings.Join(want, "\n") {
		t.Fatalf("environment = %q, want %q", environment, want)
	}
}

func TestReplaceEnvironmentKeepsTokenOutOfOtherEntries(t *testing.T) {
	t.Parallel()
	environment := replaceEnvironment(
		[]string{"PATH=/bin", "FORGEJO_TOKEN=stale", "FORGEJO_TOKEN=duplicate"},
		"FORGEJO_TOKEN",
		"current",
	)
	want := []string{"PATH=/bin", "FORGEJO_TOKEN=current"}
	if strings.Join(environment, "\n") != strings.Join(want, "\n") {
		t.Fatalf("environment = %q, want %q", environment, want)
	}
}
