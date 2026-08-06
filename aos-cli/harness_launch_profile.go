package main

import (
	"encoding/base64"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/goccy/go-yaml"
)

const (
	harnessLaunchProfilesFormat       = "agentic-os.harness-launch-profiles.v1"
	harnessLaunchProfilesRelativePath = ".agents/harness-launch-profiles.yaml"
)

var compiledHarnessLaunchProfilesBase64 string

type harnessLaunchProfileDocument struct {
	Format                 string                                     `yaml:"format"`
	Defaults               map[string]harnessLaunchProfile            `yaml:"defaults"`
	DefaultAgentGroups     map[string][]string                        `yaml:"default_agents"`
	StandaloneRoleProfiles []harnessLaunchRoleProfiles                `yaml:"standalone_role_profiles"`
	DefaultAgents          map[string]string                          `yaml:"-"`
	StandaloneRoles        map[string]map[string]harnessLaunchProfile `yaml:"-"`
}

type harnessLaunchRoleProfiles struct {
	Roles     []string                        `yaml:"roles"`
	Harnesses map[string]harnessLaunchProfile `yaml:"harnesses"`
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
	if len(document.DefaultAgentGroups) == 0 {
		return harnessLaunchProfileDocument{}, fmt.Errorf("harness launch profile default agents are empty")
	}
	document.DefaultAgents = make(map[string]string)
	for harness, roles := range document.DefaultAgentGroups {
		if _, ok := document.Defaults[harness]; !ok {
			return harnessLaunchProfileDocument{}, fmt.Errorf(
				"harness launch profile default-agent group uses unsupported harness %q",
				harness,
			)
		}
		if len(roles) == 0 {
			return harnessLaunchProfileDocument{}, fmt.Errorf(
				"harness launch profile default-agent group %s has no roles",
				harness,
			)
		}
		for _, role := range roles {
			if !safeRoleSlug(role) {
				return harnessLaunchProfileDocument{}, fmt.Errorf(
					"harness launch profile registry has unsafe default-agent role %q",
					role,
				)
			}
			if prior, ok := document.DefaultAgents[role]; ok {
				return harnessLaunchProfileDocument{}, fmt.Errorf(
					"harness launch profile role %s has duplicate default agents %s and %s",
					role,
					prior,
					harness,
				)
			}
			document.DefaultAgents[role] = harness
		}
	}
	document.StandaloneRoles = make(map[string]map[string]harnessLaunchProfile)
	for _, group := range document.StandaloneRoleProfiles {
		if len(group.Roles) == 0 {
			return harnessLaunchProfileDocument{}, fmt.Errorf("harness launch profile role group has no roles")
		}
		if len(group.Harnesses) == 0 {
			return harnessLaunchProfileDocument{}, fmt.Errorf("harness launch profile role group has no harnesses")
		}
		for harness, profile := range group.Harnesses {
			if err := validateHarnessLaunchProfile("role group", harness, profile); err != nil {
				return harnessLaunchProfileDocument{}, err
			}
		}
		for _, role := range group.Roles {
			if !safeRoleSlug(role) {
				return harnessLaunchProfileDocument{}, fmt.Errorf(
					"harness launch profile registry has unsafe role %q",
					role,
				)
			}
			if _, ok := document.DefaultAgents[role]; !ok {
				return harnessLaunchProfileDocument{}, fmt.Errorf(
					"harness launch profile role group references role %s without a default agent",
					role,
				)
			}
			profiles := document.StandaloneRoles[role]
			if profiles == nil {
				profiles = make(map[string]harnessLaunchProfile)
				document.StandaloneRoles[role] = profiles
			}
			for harness, profile := range group.Harnesses {
				if _, ok := profiles[harness]; ok {
					return harnessLaunchProfileDocument{}, fmt.Errorf(
						"harness launch profile role %s has duplicate standalone profile for %s",
						role,
						harness,
					)
				}
				profiles[harness] = profile
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

type harnessLaunchProfilesSource struct {
	label string
	data  []byte
}

func loadConfiguredHarnessLaunchProfiles() (harnessLaunchProfileDocument, error) {
	source, err := resolveHarnessLaunchProfilesSource()
	if err != nil {
		return harnessLaunchProfileDocument{}, err
	}
	document, err := loadHarnessLaunchProfiles(source.data)
	if err != nil {
		return harnessLaunchProfileDocument{}, fmt.Errorf("load %s: %w", source.label, err)
	}
	return document, nil
}

func resolveHarnessLaunchProfilesSource() (harnessLaunchProfilesSource, error) {
	if path := strings.TrimSpace(os.Getenv("AOS_HARNESS_LAUNCH_PROFILES")); path != "" {
		data, err := os.ReadFile(path)
		if err != nil {
			return harnessLaunchProfilesSource{}, fmt.Errorf("read %s: %w", path, err)
		}
		return harnessLaunchProfilesSource{label: path, data: data}, nil
	}
	for _, path := range harnessLaunchProfileCandidatePaths() {
		data, err := os.ReadFile(path)
		if err == nil {
			return harnessLaunchProfilesSource{label: path, data: data}, nil
		}
		if !errors.Is(err, fs.ErrNotExist) {
			return harnessLaunchProfilesSource{}, fmt.Errorf("read %s: %w", path, err)
		}
	}
	if strings.TrimSpace(compiledHarnessLaunchProfilesBase64) != "" {
		data, err := base64.StdEncoding.DecodeString(compiledHarnessLaunchProfilesBase64)
		if err != nil {
			return harnessLaunchProfilesSource{}, fmt.Errorf("decode compiled harness launch profiles: %w", err)
		}
		return harnessLaunchProfilesSource{label: "compiled harness launch profiles", data: data}, nil
	}
	return harnessLaunchProfilesSource{}, fmt.Errorf(
		"AOS could not find %s from the working directory or executable path",
		harnessLaunchProfilesRelativePath,
	)
}

func harnessLaunchProfileCandidatePaths() []string {
	var starts []string
	if cwd, err := os.Getwd(); err == nil {
		starts = append(starts, cwd)
	}
	if executable, err := os.Executable(); err == nil {
		starts = append(starts, filepath.Dir(executable))
	}
	var paths []string
	seen := make(map[string]bool)
	for _, start := range starts {
		start, err := filepath.Abs(start)
		if err != nil {
			continue
		}
		for {
			path := filepath.Join(start, harnessLaunchProfilesRelativePath)
			if !seen[path] {
				seen[path] = true
				paths = append(paths, path)
			}
			parent := filepath.Dir(start)
			if parent == start {
				break
			}
			start = parent
		}
	}
	return paths
}

func harnessLaunchDefaultFor(harness string) (harnessLaunchProfile, error) {
	document, err := loadConfiguredHarnessLaunchProfiles()
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
	document, err := loadConfiguredHarnessLaunchProfiles()
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
	document, err := loadConfiguredHarnessLaunchProfiles()
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
