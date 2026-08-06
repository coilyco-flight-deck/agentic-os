package main

import (
	"strings"
	"testing"
)

func TestLoadHarnessLaunchProfilesUsesDefaultsAndRoleOverrides(t *testing.T) {
	t.Parallel()
	document, err := loadHarnessLaunchProfiles([]byte(`
format: agentic-os.harness-launch-profiles.v1
defaults:
  codex:
    model: default-model
    reasoning_effort: medium
    verbosity: low
default_agents:
  director: codex
standalone_roles:
  director:
    codex:
      model: role-model
      reasoning_effort: high
`))
	if err != nil {
		t.Fatal(err)
	}
	if document.Defaults["codex"].Model != "default-model" {
		t.Fatalf("default profile was not decoded: %+v", document.Defaults["codex"])
	}
	if document.StandaloneRoles["director"]["codex"].Model != "role-model" {
		t.Fatalf(
			"standalone role profile was not decoded: %+v",
			document.StandaloneRoles["director"]["codex"],
		)
	}
	if document.DefaultAgents["director"] != "codex" {
		t.Fatalf("default agent was not decoded: %+v", document.DefaultAgents)
	}
}

func TestLoadHarnessLaunchProfilesRejectsMalformedRegistry(t *testing.T) {
	t.Parallel()
	for _, data := range [][]byte{
		[]byte(`{}`),
		[]byte("format: agentic-os.harness-launch-profiles.v1\ndefaults: {}\n"),
		[]byte("format: agentic-os.harness-launch-profiles.v1\ndefaults:\n  other:\n    model: x\n"),
		[]byte("format: agentic-os.harness-launch-profiles.v1\ndefaults:\n  codex:\n    model: ''\n"),
		[]byte("format: agentic-os.harness-launch-profiles.v1\ndefaults:\n  codex:\n    model: x\ndefault_agents:\n  bad/role: codex\n"),
		[]byte("format: agentic-os.harness-launch-profiles.v1\ndefaults:\n  codex:\n    model: x\ndefault_agents:\n  engineer: other\n"),
	} {
		if _, err := loadHarnessLaunchProfiles(data); err == nil {
			t.Fatalf("loadHarnessLaunchProfiles accepted %q", data)
		}
	}
}

func TestStandaloneDefaultAgentForRole(t *testing.T) {
	t.Parallel()
	agent, err := standaloneDefaultAgentForRole("engineer")
	if err != nil {
		t.Fatal(err)
	}
	if agent != "codex" {
		t.Fatalf("standaloneDefaultAgentForRole(engineer) = %q, want codex", agent)
	}
	for _, role := range []string{"", "bad/role", "story-architect"} {
		if _, err := standaloneDefaultAgentForRole(role); err == nil {
			t.Fatalf("standaloneDefaultAgentForRole(%q) succeeded", role)
		}
	}
}

func TestEmbeddedHarnessLaunchProfilesProduceExplicitWardEnvironment(t *testing.T) {
	t.Parallel()
	environment, err := wardLaunchEnvironmentFor("codex")
	if err != nil {
		t.Fatal(err)
	}
	rendered := strings.Join(environment, " ")
	for _, key := range []string{
		"WARD_CODEX_MODEL=",
		"WARD_CODEX_REASONING_EFFORT=",
		"WARD_CODEX_VERBOSITY=",
	} {
		if !strings.Contains(rendered, key) {
			t.Fatalf("Ward environment %q does not contain %q", rendered, key)
		}
	}
	for _, entry := range environment {
		if strings.HasSuffix(entry, "=") {
			t.Fatalf("Ward environment entry %q has an empty value", entry)
		}
	}
}

func TestStandaloneRoleTuningDoesNotChangeWardEnvironment(t *testing.T) {
	t.Parallel()
	strats, err := standaloneHarnessLaunchProfileFor("strats", "codex")
	if err != nil {
		t.Fatal(err)
	}
	engineer, err := standaloneHarnessLaunchProfileFor("engineer", "codex")
	if err != nil {
		t.Fatal(err)
	}
	if strats == engineer {
		t.Fatal("embedded standalone role tuning collapsed to one profile")
	}

	want, err := wardLaunchEnvironmentFor("codex")
	if err != nil {
		t.Fatal(err)
	}
	for _, role := range []string{"director", "engineer", "qa", "strats"} {
		plan, err := buildWardLaunchPlan(integratedLaunchOptions{
			Role: role, Agent: "codex", Image: "aos:test",
		}, "")
		if err != nil {
			t.Fatal(err)
		}
		got := plan.Environment
		if strings.Join(got, "\x00") != strings.Join(want, "\x00") {
			t.Fatalf("%s Ward environment = %v, want harness defaults %v", role, got, want)
		}
		if strings.Contains(strings.Join(plan.Args, " "), "--config") {
			t.Fatalf("%s Ward args contain a role-local config flag: %v", role, plan.Args)
		}
	}
}
