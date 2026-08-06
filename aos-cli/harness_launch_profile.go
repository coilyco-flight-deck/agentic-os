package main

import (
	_ "embed"
	"fmt"
	"strings"

	"github.com/goccy/go-yaml"
)

const harnessLaunchProfilesFormat = "agentic-os.harness-launch-profiles.v1"

//go:embed .agents/harness-launch-profiles.yaml
var embeddedHarnessLaunchProfiles []byte

type harnessLaunchProfileDocument struct {
	Format          string                                     `yaml:"format"`
	Defaults        map[string]harnessLaunchProfile            `yaml:"defaults"`
	DefaultAgents   map[string]string                          `yaml:"default_agents"`
	StandaloneRoles map[string]map[string]harnessLaunchProfile `yaml:"standalone_roles"`
}

type harnessLaunchProfile struct {
	Model           string `yaml:"model"`
	ReasoningEffort string `yaml:"reasoning_effort,omitempty"`
	Verbosity       string `yaml:"verbosity,omitempty"`
	Endpoint        string `yaml:"endpoint,omitempty"`
}

func loadHarnessLaunchProfiles(data []byte) (harnessLaunchProfileDocument, error) {
	var document harnessLaunchProfileDocument
	if err := yaml.UnmarshalWithOptions(data, &document, yaml.Strict()); err != nil {
		return harnessLaunchProfileDocument{}, fmt.Errorf("decode harness launch profiles: %w", err)
	}
	if document.Format != harnessLaunchProfilesFormat {
		return harnessLaunchProfileDocument{}, fmt.Errorf(
			"unsupported harness launch profile format %q",
			document.Format,
		)
	}
	if len(document.Defaults) == 0 {
		return harnessLaunchProfileDocument{}, fmt.Errorf("harness launch profile defaults are empty")
	}
	for harness, profile := range document.Defaults {
		if err := validateHarnessLaunchProfile("default", harness, profile); err != nil {
			return harnessLaunchProfileDocument{}, err
		}
	}
	if len(document.DefaultAgents) == 0 {
		return harnessLaunchProfileDocument{}, fmt.Errorf("harness launch profile default agents are empty")
	}
	for role, harness := range document.DefaultAgents {
		if !safeRoleSlug(role) {
			return harnessLaunchProfileDocument{}, fmt.Errorf(
				"harness launch profile registry has unsafe default-agent role %q",
				role,
			)
		}
		if _, ok := document.Defaults[harness]; !ok {
			return harnessLaunchProfileDocument{}, fmt.Errorf(
				"harness launch profile default agent %s uses unsupported harness %q",
				role,
				harness,
			)
		}
	}
	for role, profiles := range document.StandaloneRoles {
		if !safeRoleSlug(role) {
			return harnessLaunchProfileDocument{}, fmt.Errorf(
				"harness launch profile registry has unsafe role %q",
				role,
			)
		}
		for harness, profile := range profiles {
			if err := validateHarnessLaunchProfile(role, harness, profile); err != nil {
				return harnessLaunchProfileDocument{}, err
			}
		}
	}
	return document, nil
}

func validateHarnessLaunchProfile(role, harness string, profile harnessLaunchProfile) error {
	switch harness {
	case "claude", "codex", "goose", "opencode":
	default:
		return fmt.Errorf("harness launch profile %s has unsupported harness %q", role, harness)
	}
	if strings.TrimSpace(profile.Model) == "" {
		return fmt.Errorf("harness launch profile %s/%s has an empty model", role, harness)
	}
	return nil
}

func harnessLaunchDefaultFor(harness string) (harnessLaunchProfile, error) {
	document, err := loadHarnessLaunchProfiles(embeddedHarnessLaunchProfiles)
	if err != nil {
		return harnessLaunchProfile{}, err
	}
	profile, ok := document.Defaults[harness]
	if !ok {
		return harnessLaunchProfile{}, fmt.Errorf("AOS has no default launch profile for %s", harness)
	}
	return profile, nil
}

func standaloneHarnessLaunchProfileFor(role, harness string) (harnessLaunchProfile, error) {
	document, err := loadHarnessLaunchProfiles(embeddedHarnessLaunchProfiles)
	if err != nil {
		return harnessLaunchProfile{}, err
	}
	profile, ok := document.Defaults[harness]
	if !ok {
		return harnessLaunchProfile{}, fmt.Errorf("AOS has no default launch profile for %s", harness)
	}
	if override, ok := document.StandaloneRoles[role][harness]; ok {
		if override.Model != "" {
			profile.Model = override.Model
		}
		if override.ReasoningEffort != "" {
			profile.ReasoningEffort = override.ReasoningEffort
		}
		if override.Verbosity != "" {
			profile.Verbosity = override.Verbosity
		}
		if override.Endpoint != "" {
			profile.Endpoint = override.Endpoint
		}
	}
	return profile, nil
}

func standaloneDefaultAgentForRole(role string) (string, error) {
	if !safeRoleSlug(role) {
		return "", fmt.Errorf("AOS has no default agent for unsafe role %q", role)
	}
	document, err := loadHarnessLaunchProfiles(embeddedHarnessLaunchProfiles)
	if err != nil {
		return "", err
	}
	agent, ok := document.DefaultAgents[role]
	if !ok {
		return "", fmt.Errorf("AOS has no default agent for role %s; add --agent", role)
	}
	return agent, nil
}

func wardLaunchEnvironmentFor(harness string) ([]string, error) {
	profile, err := harnessLaunchDefaultFor(harness)
	if err != nil {
		return nil, err
	}
	var pairs [][2]string
	switch harness {
	case "claude":
		pairs = [][2]string{
			{"WARD_CLAUDE_MODEL", profile.Model},
			{"WARD_CLAUDE_REASONING_EFFORT", profile.ReasoningEffort},
		}
	case "codex":
		pairs = [][2]string{
			{"WARD_CODEX_MODEL", profile.Model},
			{"WARD_CODEX_REASONING_EFFORT", profile.ReasoningEffort},
			{"WARD_CODEX_VERBOSITY", profile.Verbosity},
		}
	case "goose":
		pairs = [][2]string{{"WARD_GOOSE_MODEL", profile.Model}}
	case "opencode":
		pairs = [][2]string{
			{"WARD_OPENCODE_MODEL", profile.Model},
			{"WARD_OLLAMA_URL", profile.Endpoint},
		}
	}
	environment := make([]string, 0, len(pairs))
	for _, pair := range pairs {
		if strings.TrimSpace(pair[1]) == "" {
			continue
		}
		environment = append(environment, pair[0]+"="+pair[1])
	}
	return environment, nil
}
