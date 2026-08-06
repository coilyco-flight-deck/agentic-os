package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/urfave/cli/v3"
)

const (
	contextBundleFormat       = "ward.context-bundle.v1"
	contextBundleManifestName = "context-bundle.json"
	containerBundleOutput     = "/output"
	containerComposeBundle    = "/opt/agent-compose-bundle"
)

type contextBundleManifest struct {
	Format       string                  `json:"format"`
	Role         string                  `json:"role"`
	Agent        string                  `json:"agent"`
	Repositories []string                `json:"repositories"`
	IssuePins    *contextBundleIssuePins `json:"issue_pins,omitempty"`
}

type contextBundleIssuePins struct {
	Digest string `json:"digest"`
}

type contextBundlePlanOptions struct {
	Image           string
	Role            string
	Agent           string
	Delivery        string
	Composed        bool
	Guarded         bool
	Output          string
	UID             int
	GID             int
	Bundle          string
	IssuePinContext issuePinLaunchContext
}

type contextBundlePlan struct {
	DockerArgs []string
}

type contextBundleMaterializeOptions struct {
	Image           string
	Role            string
	Agent           string
	Delivery        string
	Composed        bool
	Guarded         bool
	Bundle          string
	IssuePinContext issuePinLaunchContext
}

func buildContextBundlePlan(opts contextBundlePlanOptions) (contextBundlePlan, error) {
	if strings.TrimSpace(opts.Image) == "" {
		return contextBundlePlan{}, fmt.Errorf("context-bundle image must not be empty")
	}
	if !safeRoleSlug(opts.Role) {
		return contextBundlePlan{}, fmt.Errorf("invalid context-bundle role %q", opts.Role)
	}
	if _, _, err := selectedContextLayout(opts.Agent); err != nil {
		return contextBundlePlan{}, err
	}
	if !opts.Composed && !opts.Guarded {
		return contextBundlePlan{}, fmt.Errorf("context bundle needs composed context, guarded tools, or both")
	}
	if strings.TrimSpace(opts.Output) == "" {
		return contextBundlePlan{}, fmt.Errorf("context-bundle output must not be empty")
	}
	if opts.UID < 0 || opts.GID < 0 {
		return contextBundlePlan{}, fmt.Errorf("uid and gid must be non-negative")
	}

	args := []string{
		"run",
		"--rm",
		"--label", "aos.context-bundle=1",
		"--mount", "type=bind,source=" + opts.Output + ",target=" + containerBundleOutput,
	}
	if opts.Composed {
		if strings.TrimSpace(opts.Bundle) == "" {
			return contextBundlePlan{}, fmt.Errorf("composed context bundle needs a verified Agent Compose bundle")
		}
		args = append(args,
			"--mount",
			"type=bind,source="+opts.Bundle+",target="+containerComposeBundle+",readonly",
		)
	}
	if opts.IssuePinContext.HostPath != "" {
		info, err := os.Stat(opts.IssuePinContext.HostPath)
		if err != nil {
			return contextBundlePlan{}, fmt.Errorf("inspect issue-pin context: %w", err)
		}
		if !info.Mode().IsRegular() {
			return contextBundlePlan{}, fmt.Errorf("issue-pin context %s is not a regular file", opts.IssuePinContext.HostPath)
		}
		args = append(args,
			"--mount",
			"type=bind,source="+opts.IssuePinContext.HostPath+",target="+containerIssuePinContext+",readonly",
		)
	}
	args = append(args,
		"--tmpfs", "/tmp:rw,exec,size="+runtimeTmpfsSize,
		"--env", "AOS_CONTAINER=1",
		"--entrypoint", "/usr/local/bin/aos",
		opts.Image,
		"--role", opts.Role,
		"--agent", opts.Agent,
		"--layout", opts.Agent,
		"--delivery", opts.Delivery,
	)
	if opts.Composed {
		args = append(args, "--composed")
	}
	if opts.Guarded {
		args = append(args, "--guarded")
	}
	args = append(args,
		"_container-context-bundle",
		"--output", containerBundleOutput,
		"--uid", fmt.Sprintf("%d", opts.UID),
		"--gid", fmt.Sprintf("%d", opts.GID),
	)
	if opts.Composed {
		args = append(args, "--bundle", containerComposeBundle)
	}
	if opts.IssuePinContext.HostPath != "" {
		args = append(
			args,
			"--issue-pin-context", containerIssuePinContext,
			"--issue-pin-digest", opts.IssuePinContext.Digest,
		)
	}

	return contextBundlePlan{DockerArgs: args}, nil
}

func materializeContextBundle(
	ctx context.Context,
	opts contextBundleMaterializeOptions,
) (string, error) {
	if _, err := hostLookPath("docker"); err != nil {
		return "", fmt.Errorf("context materialization needs Docker on the host PATH: %w", err)
	}
	cache, err := os.UserCacheDir()
	if err != nil {
		return "", fmt.Errorf("resolve AOS cache directory: %w", err)
	}
	root := filepath.Join(cache, "aos", "context-bundles")
	if err := os.MkdirAll(root, 0o700); err != nil {
		return "", fmt.Errorf("create AOS context-bundle cache: %w", err)
	}
	staging, err := os.MkdirTemp(root, ".staging-")
	if err != nil {
		return "", fmt.Errorf("create context-bundle staging directory: %w", err)
	}
	published := false
	defer func() {
		if !published {
			_ = os.RemoveAll(staging)
		}
	}()

	uid, gid := hostIdentity()
	composeBundle := ""
	if opts.Composed {
		composeBundle, err = materializeAgentComposeBundle(ctx, opts.Role, opts.Agent)
		if err != nil {
			return "", err
		}
	}
	issuePins, err := prepareIssuePinLaunchContext(ctx, opts.Role)
	if err != nil {
		return "", err
	}
	defer func() { _ = issuePins.Close() }()
	plan, err := buildContextBundlePlan(contextBundlePlanOptions{
		Image:           opts.Image,
		Role:            opts.Role,
		Agent:           opts.Agent,
		Delivery:        opts.Delivery,
		Composed:        opts.Composed,
		Guarded:         opts.Guarded,
		Output:          staging,
		UID:             uid,
		GID:             gid,
		Bundle:          composeBundle,
		IssuePinContext: issuePins,
	})
	if err != nil {
		return "", err
	}
	if err := runDocker(ctx, plan.DockerArgs); err != nil {
		return "", fmt.Errorf("materialize context bundle: %w", err)
	}
	if err := validateContextBundleOutput(staging, opts); err != nil {
		return "", err
	}
	digest, err := hashContextBundle(staging)
	if err != nil {
		return "", err
	}
	destination := filepath.Join(
		root,
		fmt.Sprintf("%s-%s-%s", opts.Role, opts.Agent, digest[:24]),
	)
	if _, err := os.Stat(destination); err == nil {
		existingDigest, hashErr := hashContextBundle(destination)
		if hashErr != nil {
			return "", hashErr
		}
		if existingDigest != digest {
			return "", fmt.Errorf("context-bundle cache collision at %s", destination)
		}
		return destination, nil
	} else if !os.IsNotExist(err) {
		return "", fmt.Errorf("inspect context-bundle cache destination: %w", err)
	}
	if err := os.Rename(staging, destination); err != nil {
		return "", fmt.Errorf("publish immutable context bundle: %w", err)
	}
	published = true
	if err := makeTreeReadOnly(destination); err != nil {
		return "", fmt.Errorf("make context bundle immutable: %w", err)
	}
	return destination, nil
}

func materializeAgentComposeBundle(ctx context.Context, role, agent string) (string, error) {
	binary, err := hostLookPath("agent-compose")
	if err != nil {
		return "", fmt.Errorf("context materialization needs Agent Compose on the host PATH: %w", err)
	}
	command := exec.CommandContext(
		ctx,
		binary,
		"bundle", "materialize",
		"--role", role,
		"--harness", agent,
	)
	command.Stderr = os.Stderr
	raw, err := command.Output()
	if err != nil {
		return "", fmt.Errorf("materialize verified Agent Compose bundle: %w", err)
	}
	var selected struct {
		Format string `json:"format"`
		Bundle string `json:"bundle"`
	}
	decoder := json.NewDecoder(strings.NewReader(string(raw)))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&selected); err != nil {
		return "", fmt.Errorf("decode Agent Compose bundle selection: %w", err)
	}
	if selected.Format != "agent-compose.bundle-selection.v1" || strings.TrimSpace(selected.Bundle) == "" {
		return "", fmt.Errorf("Agent Compose returned an invalid bundle selection")
	}
	verify := exec.CommandContext(ctx, binary, "verify", selected.Bundle)
	verify.Stdout = os.Stderr
	verify.Stderr = os.Stderr
	if err := verify.Run(); err != nil {
		return "", fmt.Errorf("verify selected Agent Compose bundle: %w", err)
	}
	if _, err := readBundleRepositories(selected.Bundle, role); err != nil {
		return "", err
	}
	return selected.Bundle, nil
}

func projectVerifiedBundle(
	ctx context.Context,
	opts bootstrapOptions,
	bundle string,
	runner commandRunner,
) error {
	if err := runner.Run(ctx, opts.AgentComposeBin, "verify", bundle); err != nil {
		return fmt.Errorf("verify Agent Compose context bundle: %w", err)
	}
	if _, err := readBundleRepositories(bundle, opts.Role); err != nil {
		return err
	}
	if err := runner.Run(
		ctx,
		opts.AgentComposeBin,
		"project", bundle,
		"--layout", opts.Layout,
		"--target", opts.AgentHome,
		"--scope", "home",
	); err != nil {
		return fmt.Errorf("project Agent Compose context bundle: %w", err)
	}
	return nil
}

func readBundleRepositories(bundle, role string) ([]string, error) {
	raw, err := os.ReadFile(filepath.Join(bundle, "manifest.json"))
	if err != nil {
		return nil, fmt.Errorf("read Agent Compose bundle manifest: %w", err)
	}
	var manifest struct {
		Format       string `json:"format"`
		Role         string `json:"role"`
		Repositories []struct {
			Identity string `json:"identity"`
		} `json:"repositories"`
	}
	if err := json.Unmarshal(raw, &manifest); err != nil {
		return nil, fmt.Errorf("decode Agent Compose bundle manifest: %w", err)
	}
	if manifest.Format != "agent-compose.bundle" || manifest.Role != role {
		return nil, fmt.Errorf("Agent Compose bundle does not match selected role %q", role)
	}
	repositories := make([]string, 0, len(manifest.Repositories))
	prior := ""
	for _, repository := range manifest.Repositories {
		parts := strings.Split(repository.Identity, "/")
		if len(parts) != 2 || !safePathSegment(parts[0]) || !safePathSegment(parts[1]) {
			return nil, fmt.Errorf("Agent Compose bundle contains invalid repository identity %q", repository.Identity)
		}
		if repository.Identity <= prior {
			return nil, fmt.Errorf("Agent Compose bundle repositories are not strictly sorted and deduplicated")
		}
		prior = repository.Identity
		repositories = append(repositories, repository.Identity)
	}
	if len(repositories) == 0 {
		return nil, fmt.Errorf("Agent Compose bundle selects no repositories")
	}
	return repositories, nil
}

func runContainerContextBundle(ctx context.Context, cmd *cli.Command) error {
	if os.Getenv("AOS_CONTAINER") != "1" {
		return fmt.Errorf("_container-context-bundle is internal to an AOS container")
	}
	opts := bootstrapDefaults(bootstrapOptions{
		Role:      strings.TrimSpace(cmd.String("role")),
		Layout:    strings.TrimSpace(cmd.String("layout")),
		Delivery:  strings.TrimSpace(cmd.String("delivery")),
		Composed:  cmd.Bool("composed"),
		Guarded:   cmd.Bool("guarded"),
		AgentHome: filepath.Join(cmd.String("output"), "home"),
		UID:       cmd.Int("uid"),
		GID:       cmd.Int("gid"),
	})
	if opts.Role == "" {
		return fmt.Errorf("_container-context-bundle needs --role")
	}
	if !opts.Composed && !opts.Guarded {
		return fmt.Errorf("_container-context-bundle needs --composed, --guarded, or both")
	}
	output, err := filepath.Abs(strings.TrimSpace(cmd.String("output")))
	if err != nil {
		return fmt.Errorf("resolve context-bundle output: %w", err)
	}
	if err := requireEmptyDirectory(output); err != nil {
		return err
	}
	opts.AgentHome = filepath.Join(output, "home")
	if err := os.MkdirAll(opts.AgentHome, 0o755); err != nil {
		return fmt.Errorf("create context-bundle home: %w", err)
	}

	if opts.Composed {
		composeBundle := strings.TrimSpace(cmd.String("bundle"))
		if composeBundle == "" {
			return fmt.Errorf("_container-context-bundle needs --bundle for composed context")
		}
		if err := projectVerifiedBundle(ctx, opts, composeBundle, osCommandRunner{}); err != nil {
			return err
		}
		if err := os.RemoveAll(filepath.Join(opts.AgentHome, ".agent-compose")); err != nil {
			return fmt.Errorf("remove agent-compose projection state: %w", err)
		}
	}
	if opts.Guarded {
		if err := stageAOSGuardContext(opts.Layout, opts.Role, opts.AgentHome, opts.AOSGuardSkill); err != nil {
			return err
		}
		if err := stageAOSGuardBinary(output, opts.AOSGuardBinary); err != nil {
			return err
		}
	}
	issuePinContext := strings.TrimSpace(cmd.String("issue-pin-context"))
	issuePinDigest := strings.TrimSpace(cmd.String("issue-pin-digest"))
	if err := stageHydratedIssuePinContext(opts.Layout, opts.AgentHome, issuePinContext, issuePinDigest); err != nil {
		return err
	}
	if err := validateStagedHome(opts.AgentHome, opts.Layout); err != nil {
		return err
	}
	manifest := contextBundleManifest{
		Format: contextBundleFormat,
		Role:   opts.Role,
		Agent:  opts.Layout,
	}
	if opts.Composed {
		repositories, err := readBundleRepositories(strings.TrimSpace(cmd.String("bundle")), opts.Role)
		if err != nil {
			return err
		}
		manifest.Repositories = repositories
	}
	if issuePinContext != "" {
		manifest.IssuePins = &contextBundleIssuePins{Digest: issuePinDigest}
	}
	body, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return fmt.Errorf("encode context-bundle manifest: %w", err)
	}
	body = append(body, '\n')
	if err := os.WriteFile(filepath.Join(output, contextBundleManifestName), body, 0o644); err != nil {
		return fmt.Errorf("write context-bundle manifest: %w", err)
	}
	if err := chownTree(output, opts.UID, opts.GID); err != nil {
		return fmt.Errorf("hand off context bundle: %w", err)
	}
	return nil
}

func requireEmptyDirectory(path string) error {
	info, err := os.Lstat(path)
	if err != nil {
		return fmt.Errorf("inspect context-bundle output: %w", err)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
		return fmt.Errorf("context-bundle output %s must be an existing real directory", path)
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return fmt.Errorf("read context-bundle output: %w", err)
	}
	if len(entries) != 0 {
		return fmt.Errorf("context-bundle output %s must be empty", path)
	}
	return nil
}

func stageAOSGuardBinary(output, source string) error {
	info, err := os.Stat(source)
	if err != nil {
		return fmt.Errorf("inspect aosguard binary: %w", err)
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("aosguard binary %s is not a regular file", source)
	}
	bin := filepath.Join(output, "bin")
	if err := os.MkdirAll(bin, 0o755); err != nil {
		return fmt.Errorf("create context-bundle tool directory: %w", err)
	}
	target := filepath.Join(bin, "aosguard")
	if err := copyFile(source, target, 0o755); err != nil {
		return fmt.Errorf("stage aosguard binary: %w", err)
	}
	return nil
}

func validateStagedHome(home, layout string) error {
	instruction, skills, err := selectedContextLayout(layout)
	if err != nil {
		return err
	}
	hasInstruction := false
	err = filepath.WalkDir(home, func(full string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(home, full)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		if rel == "." {
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("staged home path %q is a symbolic link", rel)
		}
		if entry.IsDir() {
			if rel == skills ||
				strings.HasPrefix(rel, skills+"/") ||
				strings.HasPrefix(instruction, rel+"/") ||
				strings.HasPrefix(skills, rel+"/") {
				return nil
			}
			return fmt.Errorf("staged home directory %q is outside the selected %s layout", rel, layout)
		}
		if !info.Mode().IsRegular() {
			return fmt.Errorf("staged home path %q is not a regular file", rel)
		}
		if rel == instruction {
			hasInstruction = true
			return nil
		}
		if strings.HasPrefix(rel, skills+"/") {
			return nil
		}
		return fmt.Errorf("staged home path %q is outside the selected %s layout", rel, layout)
	})
	if err != nil {
		return fmt.Errorf("validate staged home: %w", err)
	}
	if !hasInstruction {
		return fmt.Errorf("staged home is missing selected %s instruction file %s", layout, instruction)
	}
	return nil
}

func validateContextBundleOutput(
	root string,
	expected contextBundleMaterializeOptions,
) error {
	manifestFile, err := os.Open(filepath.Join(root, contextBundleManifestName))
	if err != nil {
		return fmt.Errorf("open materialized context-bundle manifest: %w", err)
	}
	defer manifestFile.Close()
	decoder := json.NewDecoder(io.LimitReader(manifestFile, 64*1024))
	decoder.DisallowUnknownFields()
	var manifest contextBundleManifest
	if err := decoder.Decode(&manifest); err != nil {
		return fmt.Errorf("decode materialized context-bundle manifest: %w", err)
	}
	var trailing json.RawMessage
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		return fmt.Errorf("materialized context-bundle manifest has trailing JSON")
	}
	if manifest.Format != contextBundleFormat ||
		manifest.Role != expected.Role ||
		manifest.Agent != expected.Agent {
		return fmt.Errorf("materialized context-bundle manifest does not match the selected launch")
	}
	if expected.Composed && len(manifest.Repositories) == 0 {
		return fmt.Errorf("materialized composed context bundle selects no repositories")
	}
	if !expected.Composed && len(manifest.Repositories) != 0 {
		return fmt.Errorf("materialized uncomposed context bundle unexpectedly selects repositories")
	}
	prior := ""
	for _, repository := range manifest.Repositories {
		parts := strings.Split(repository, "/")
		if len(parts) != 2 || !safePathSegment(parts[0]) || !safePathSegment(parts[1]) || repository <= prior {
			return fmt.Errorf("materialized context bundle has invalid, unsorted, or duplicate repository %q", repository)
		}
		prior = repository
	}
	if manifest.IssuePins != nil && !safeHexDigest(manifest.IssuePins.Digest) {
		return fmt.Errorf("materialized context bundle has invalid issue-pin digest")
	}
	if err := validateStagedHome(filepath.Join(root, "home"), expected.Agent); err != nil {
		return err
	}
	bin := filepath.Join(root, "bin")
	if expected.Guarded {
		info, err := os.Stat(filepath.Join(bin, "aosguard"))
		if err != nil || !info.Mode().IsRegular() {
			return fmt.Errorf("materialized guarded bundle is missing bin/aosguard")
		}
	} else if _, err := os.Stat(bin); !os.IsNotExist(err) {
		return fmt.Errorf("materialized unguarded bundle unexpectedly contains bin")
	}
	return nil
}

func safeHexDigest(value string) bool {
	if len(value) != sha256.Size*2 {
		return false
	}
	for _, r := range value {
		if (r >= '0' && r <= '9') || (r >= 'a' && r <= 'f') {
			continue
		}
		return false
	}
	return true
}

func hashContextBundle(root string) (string, error) {
	hash := sha256.New()
	err := filepath.WalkDir(root, func(full string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(root, full)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		if rel == "." {
			return nil
		}
		if _, err := io.WriteString(hash, rel+"\x00"); err != nil {
			return err
		}
		if entry.IsDir() {
			_, err := io.WriteString(hash, "dir\x00")
			return err
		}
		file, err := os.Open(full)
		if err != nil {
			return err
		}
		_, copyErr := io.Copy(hash, file)
		closeErr := file.Close()
		if copyErr != nil {
			return copyErr
		}
		if closeErr != nil {
			return closeErr
		}
		_, err = io.WriteString(hash, "\x00")
		return err
	})
	if err != nil {
		return "", fmt.Errorf("hash context bundle: %w", err)
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}
