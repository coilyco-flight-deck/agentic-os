package main

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/goccy/go-yaml"
)

func testGit(t *testing.T, directory string, args ...string) string {
	t.Helper()
	command := exec.Command("git", append([]string{"-C", directory}, args...)...)
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("git -C %s %s: %v\n%s",
			directory, strings.Join(args, " "), err, output)
	}
	return strings.TrimSpace(string(output))
}

func createNativeTestRepository(
	t *testing.T,
	root string,
	owner string,
	name string,
) (string, string) {
	t.Helper()
	remote := filepath.Join(root, "remotes", owner, name+".git")
	repository := filepath.Join(root, "projects", owner, name)
	if err := os.MkdirAll(filepath.Dir(remote), 0o755); err != nil {
		t.Fatal(err)
	}
	testGit(t, root, "init", "--bare", "--initial-branch=main", remote)
	if err := os.MkdirAll(repository, 0o755); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "init", "--initial-branch=main")
	testGit(t, repository, "config", "user.email", "test@example.com")
	testGit(t, repository, "config", "user.name", "AOS Test")
	if err := os.WriteFile(filepath.Join(repository, "README.md"), []byte("test\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", "README.md")
	testGit(t, repository, "commit", "-m", "initial")
	testGit(t, repository, "remote", "add", "origin", "file://"+remote)
	testGit(t, repository, "push", "-u", "origin", "main")
	return repository, remote
}

func nativeTestRuntime(t *testing.T, root string) nativeRuntime {
	t.Helper()
	start, err := processStartIdentity(os.Getpid())
	if err != nil {
		t.Fatal(err)
	}
	expected := filepath.Join(root, "expected.txt")
	fleet := filepath.Join(root, "fleet.txt")
	home := filepath.Join(root, "home")
	if err := os.MkdirAll(home, 0o755); err != nil {
		t.Fatal(err)
	}
	return nativeRuntime{
		Now:          time.Date(2026, 7, 29, 10, 0, 0, 0, time.UTC),
		PID:          os.Getpid(),
		ProcessStart: start,
		CWD:          filepath.Join(root, "projects"),
		Home:         home,
		ProjectsRoot: filepath.Join(root, "projects"),
		StateRoot:    filepath.Join(root, "state"),
		SessionsRoot: filepath.Join(root, "sessions"),
		PlanFile:     expected,
		FleetFile:    fleet,
		Stderr:       os.Stderr,
	}
}

func writeNativeTestList(t *testing.T, path string, values ...string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(strings.Join(values, "\n")+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}

func writeNativeTestPlan(t *testing.T, path string, values ...string) {
	t.Helper()
	identities := make([]string, 0, len(values))
	for _, value := range values {
		if !strings.Contains(value, "/") {
			value = "owner/" + value
		}
		identities = append(identities, value)
	}
	slices.Sort(identities)
	residency := make([]aosRepositorySelection, 0, len(identities))
	for _, identity := range identities {
		residency = append(residency, aosRepositorySelection{
			Identity: identity,
			Path:     filepath.Join(filepath.Dir(path), "projects", filepath.FromSlash(identity)),
			Source:   "test", Scope: "role-union", Reason: "test repository",
		})
	}
	payload := aosRepositoryPlan{
		Format:       agentComposeRepositoryPlanYAMLFormat,
		ProjectsRoot: filepath.Join(filepath.Dir(path), "projects"),
		Inputs: []aosRepositoryPlanInput{{
			Identity: "owner/policy", Revision: "0123456789abcdef",
			Policy: aosRepositoryPolicyInput{Path: ".agents/roles.kdl", SHA256: "sha256:test"},
		}},
		Roles:     map[string][]aosRepositorySelection{},
		Residency: residency,
	}
	raw, err := yaml.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}

func onlyNativeLease(t *testing.T, runtime nativeRuntime) (string, nativeLease) {
	t.Helper()
	entries, err := os.ReadDir(nativeStatePath(runtime, "leases"))
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 {
		t.Fatalf("got %d leases, want 1", len(entries))
	}
	path := nativeStatePath(runtime, "leases", entries[0].Name())
	var lease nativeLease
	if err := readNativeJSON(path, &lease); err != nil {
		t.Fatal(err)
	}
	return path, lease
}

func TestNativeLaunchCreatesFleetWorkspaceFromProjectsRoot(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	createNativeTestRepository(t, root, "owner", "two")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one", "two")
	writeNativeTestList(t, runtime.FleetFile, "owner")

	launch, err := prepareNativeLaunch(runtime, "codex")
	if err != nil {
		t.Fatal(err)
	}

	if samePath(launch, runtime.ProjectsRoot) {
		t.Fatal("launch stayed in canonical projects root")
	}
	for _, name := range []string{"one", "two"} {
		if _, err := os.Stat(filepath.Join(launch, "owner", name, "README.md")); err != nil {
			t.Fatalf("%s worktree missing: %v", name, err)
		}
	}
	_, lease := onlyNativeLease(t, runtime)
	if len(lease.Artifacts) != 2 {
		t.Fatalf("got %d artifacts, want 2", len(lease.Artifacts))
	}
}

func TestNativeLaunchMapsRepositorySubdirectoryIntoSession(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	if err := os.MkdirAll(filepath.Join(repository, "docs"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(repository, "docs", "README.md"), []byte("docs\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", "docs/README.md")
	testGit(t, repository, "commit", "-m", "add docs")
	testGit(t, repository, "push", "origin", "main")
	runtime := nativeTestRuntime(t, root)
	runtime.CWD = filepath.Join(repository, "docs")
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")

	launch, err := prepareNativeLaunch(runtime, "claude")
	if err != nil {
		t.Fatal(err)
	}

	if filepath.Base(launch) != "docs" || strings.Contains(launch, repository) {
		t.Fatalf("mapped launch = %s", launch)
	}
}

func TestNativeLaunchCanStartAtSessionProjectsRoot(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	runtime.CWD = repository
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	t.Setenv(agentComposeRuntimeHomeEnv, "")

	launch, err := prepareNativeLaunchWithOptions(
		runtime,
		"codex",
		nativeLaunchOptions{WorkspaceRoot: true},
	)
	if err != nil {
		t.Fatal(err)
	}

	_, lease := onlyNativeLease(t, runtime)
	if !samePath(launch, lease.SessionProjects) {
		t.Fatalf("launch = %s, want session projects %s", launch, lease.SessionProjects)
	}
	if got := os.Getenv(agentComposeRuntimeHomeEnv); got != lease.SessionHome {
		t.Fatalf("runtime home = %s, want %s", got, lease.SessionHome)
	}
}

func TestStageNativeRoleHomeFiltersUserSkills(t *testing.T) {
	source := filepath.Join(t.TempDir(), "source")
	target := filepath.Join(t.TempDir(), "target")
	for _, path := range []string{
		filepath.Join(source, ".agents", "skills", "role-other"),
		filepath.Join(source, ".claude", "skills", "role-other"),
		filepath.Join(source, ".config"),
	} {
		if err := os.MkdirAll(path, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	for _, path := range []string{
		filepath.Join(source, ".agents", "settings.json"),
		filepath.Join(source, ".claude", "settings.json"),
		filepath.Join(source, ".gitconfig"),
	} {
		if err := os.WriteFile(path, []byte("test\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	if err := stageNativeRoleHome(source, target); err != nil {
		t.Fatal(err)
	}

	for _, path := range []string{
		filepath.Join(target, ".agents", "skills"),
		filepath.Join(target, ".claude", "skills"),
	} {
		entries, err := os.ReadDir(path)
		if err != nil {
			t.Fatal(err)
		}
		if len(entries) != 0 {
			t.Fatalf("filtered skills remain under %s: %+v", path, entries)
		}
	}
	for _, path := range []string{
		filepath.Join(target, ".agents", "settings.json"),
		filepath.Join(target, ".claude", "settings.json"),
		filepath.Join(target, ".config"),
		filepath.Join(target, ".gitconfig"),
	} {
		info, err := os.Lstat(path)
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode()&os.ModeSymlink == 0 {
			t.Errorf("preserved native home entry is not a symlink: %s", path)
		}
	}
}

func TestStageStandaloneRoleHomeCopiesSafeConfigAndDeniesSensitivePaths(t *testing.T) {
	source := filepath.Join(t.TempDir(), "source")
	target := filepath.Join(t.TempDir(), "target")
	for _, path := range []string{
		filepath.Join(source, ".agents", "skills", "role-other"),
		filepath.Join(source, ".agents", "profiles"),
		filepath.Join(source, ".claude", "skills", "role-other"),
		filepath.Join(source, ".aws"),
		filepath.Join(source, ".codex"),
		filepath.Join(source, ".config", "goose"),
	} {
		if err := os.MkdirAll(path, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	for _, path := range []string{
		filepath.Join(source, ".agents", "settings.json"),
		filepath.Join(source, ".agents", "profiles", "engineer.yaml"),
		filepath.Join(source, ".agents", "skills", "role-other", "SKILL.md"),
		filepath.Join(source, ".claude", "settings.json"),
		filepath.Join(source, ".claude", ".credentials.json"),
		filepath.Join(source, ".aws", "config"),
		filepath.Join(source, ".codex", "auth.json"),
		filepath.Join(source, ".config", "goose", "config.yaml"),
		filepath.Join(source, ".gitconfig"),
	} {
		if err := os.WriteFile(path, []byte("test\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	if err := stageStandaloneRoleHome(source, target); err != nil {
		t.Fatal(err)
	}

	for _, path := range []string{
		filepath.Join(target, ".agents", "settings.json"),
		filepath.Join(target, ".agents", "profiles", "engineer.yaml"),
		filepath.Join(target, ".claude", "settings.json"),
	} {
		info, err := os.Lstat(path)
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode()&os.ModeSymlink != 0 {
			t.Errorf("standalone home entry should be copied, not symlinked: %s", path)
		}
	}
	for _, path := range []string{
		filepath.Join(target, ".agents", "skills", "role-other", "SKILL.md"),
		filepath.Join(target, ".claude", "skills", "role-other"),
		filepath.Join(target, ".claude", ".credentials.json"),
		filepath.Join(target, ".aws", "config"),
		filepath.Join(target, ".codex", "auth.json"),
		filepath.Join(target, ".config", "goose", "config.yaml"),
		filepath.Join(target, ".gitconfig"),
	} {
		if _, err := os.Lstat(path); !os.IsNotExist(err) {
			t.Fatalf("standalone home projected denied path %s: %v", path, err)
		}
	}
	for _, path := range []string{
		filepath.Join(target, ".agents", "skills"),
		filepath.Join(target, ".claude", "skills"),
	} {
		entries, err := os.ReadDir(path)
		if err != nil {
			t.Fatal(err)
		}
		if len(entries) != 0 {
			t.Fatalf("standalone skill directory is not empty under %s: %+v", path, entries)
		}
	}
}

func TestNativeShadowExportsAOSModelTier(t *testing.T) {
	t.Setenv(agentComposeModelClassEnv, "legacy-model-class")
	t.Setenv(agentComposeModelTierEnv, "")

	command := []string{
		"agent-compose", "launch", "engineer", "goose",
		"--model", "deploy-backend/deepseek-v4-flash",
	}
	if err := applyNativeModelTier("goose", command); err != nil {
		t.Fatal(err)
	}
	if got := os.Getenv(agentComposeModelTierEnv); got != modelTierCommodity {
		t.Fatalf("model tier = %q, want %s", got, modelTierCommodity)
	}
	if _, found := os.LookupEnv(agentComposeModelClassEnv); found {
		t.Fatalf("retired %s remains set", agentComposeModelClassEnv)
	}
}

func TestConvergeNativeEnvironmentAppliesHostMCPProjection(t *testing.T) {
	root := t.TempDir()
	runtime := nativeTestRuntime(t, root)
	config := filepath.Join(runtime.Home, ".config", "aos", "converge.yaml")
	inventory := filepath.Join(runtime.Home, ".config", "mcporter", "mcporter.json")
	writeNativeMCPTestFile(
		t,
		config,
		"mcp:\n  inventory: ~/.config/mcporter/mcporter.json\n",
	)
	writeNativeMCPTestFile(
		t,
		inventory,
		`{"imports":[],"mcpServers":{"forgejo":{"baseUrl":"https://mcp.example.test/mcp","x-codex":{"defaultToolsApprovalMode":"approve"}}}}`+"\n",
	)

	if err := convergeNativeEnvironment(context.Background(), runtime); err != nil {
		t.Fatal(err)
	}

	raw, err := os.ReadFile(filepath.Join(runtime.Home, ".codex", "config.toml"))
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{
		aosMCPBlockBegin,
		`[mcp_servers."forgejo"]`,
		`default_tools_approval_mode = "approve"`,
	} {
		if !strings.Contains(string(raw), want) {
			t.Fatalf("native convergence missing %q:\n%s", want, raw)
		}
	}
}

func TestNativeShadowProtectsClaudeInstall(t *testing.T) {
	tests := []struct {
		name     string
		harness  string
		isolated bool
		want     string
	}{
		{name: "isolated Claude", harness: "claude", isolated: true, want: "1"},
		{name: "host Claude", harness: "claude", isolated: false, want: "original"},
		{name: "isolated Codex", harness: "codex", isolated: true, want: "original"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Setenv(claudeDisableAutoUpdaterEnv, "original")

			if err := protectNativeHarnessInstall(test.harness, test.isolated); err != nil {
				t.Fatal(err)
			}
			if got := os.Getenv(claudeDisableAutoUpdaterEnv); got != test.want {
				t.Fatalf("%s = %q, want %q", claudeDisableAutoUpdaterEnv, got, test.want)
			}
		})
	}
}

func TestNativeCodexWorkspaceTrustIsScopedToGeneratedProject(t *testing.T) {
	project := "/tmp/aos/native/session/projects"
	override := `projects={"/tmp/aos/native/session/projects"={trust_level="trusted"}}`
	tests := []struct {
		name    string
		command []string
		want    []string
	}{
		{
			name:    "assigned role",
			command: []string{"agent-compose", "launch", "engineer", "codex", "--model", "gpt"},
			want:    []string{"agent-compose", "launch", "engineer", "codex", "--config", override, "--model", "gpt"},
		},
		{
			name:    "inferred role",
			command: []string{"agent-compose", "compose", "--", "codex", "--model", "gpt"},
			want:    []string{"agent-compose", "compose", "--", "codex", "--config", override, "--model", "gpt"},
		},
		{
			name:    "direct harness",
			command: []string{"codex", "--model", "gpt"},
			want:    []string{"codex", "--config", override, "--model", "gpt"},
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got := trustNativeCodexWorkspace(test.command, "codex", project)
			if strings.Join(got, "\x00") != strings.Join(test.want, "\x00") {
				t.Fatalf("command = %#v, want %#v", got, test.want)
			}
		})
	}
}

func TestNativeCodexProjectResolvesWorkspaceSymlinks(t *testing.T) {
	actual := filepath.Join(t.TempDir(), "projects")
	if err := os.MkdirAll(actual, 0o755); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(t.TempDir(), "projects")
	if err := os.Symlink(actual, link); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	resolved, err := filepath.EvalSymlinks(actual)
	if err != nil {
		t.Fatal(err)
	}

	if got := nativeCodexProject(link); got != resolved {
		t.Fatalf("project = %q, want canonical path %q", got, resolved)
	}
}

func TestNativeWorkspaceTrustDoesNotChangeOtherHarnesses(t *testing.T) {
	command := []string{"agent-compose", "launch", "engineer", "claude"}
	got := trustNativeCodexWorkspace(command, "claude", "/tmp/aos/native/session/projects")
	if strings.Join(got, "\x00") != strings.Join(command, "\x00") {
		t.Fatalf("command = %#v, want unchanged %#v", got, command)
	}
}

func TestNativeLaunchOutsideProjectsStillCreatesFleetWorkspace(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	runtime.CWD = root
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")

	launch, err := prepareNativeLaunch(runtime, "codex")
	if err != nil {
		t.Fatal(err)
	}

	if launch != runtime.CWD {
		t.Fatalf("launch = %s, want original directory %s", launch, runtime.CWD)
	}
	_, lease := onlyNativeLease(t, runtime)
	if len(lease.Artifacts) != 1 {
		t.Fatalf("got %d artifacts, want 1", len(lease.Artifacts))
	}
}

func TestNativeLaunchMapsOwnerDirectoryIntoSession(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	runtime.CWD = filepath.Join(runtime.ProjectsRoot, "owner")
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")

	launch, err := prepareNativeLaunch(runtime, "codex")
	if err != nil {
		t.Fatal(err)
	}

	if filepath.Base(launch) != "owner" || samePath(launch, runtime.CWD) {
		t.Fatalf("mapped owner launch = %s", launch)
	}
}

func TestLegacyDeadSessionIsCleanedAfterGrace(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}
	leasePath, lease := onlyNativeLease(t, runtime)
	oldWorktree := lease.Artifacts[0].Worktree
	oldBranch := lease.Artifacts[0].Branch
	lease.PID = 0
	lease.ProcessStart = ""
	if err := writeNativeJSON(leasePath, lease); err != nil {
		t.Fatal(err)
	}
	runtime.Now = runtime.Now.Add(time.Minute)

	live, err := cleanDeadNativeSessions(runtime)
	if err != nil {
		t.Fatal(err)
	}
	var retained nativeLease
	if err := readNativeJSON(leasePath, &retained); err != nil {
		t.Fatal(err)
	}
	if retained.DeadSince == nil || !retained.DeadSince.Equal(runtime.Now) {
		t.Fatalf("dead since = %v, want %s", retained.DeadSince, runtime.Now)
	}
	if !live.contains(oldWorktree) {
		t.Fatal("newly dead worktree was not protected from the fleet sweep")
	}
	if _, err := os.Stat(oldWorktree); err != nil {
		t.Fatalf("newly dead worktree was removed: %v", err)
	}

	runtime.Now = runtime.Now.Add(nativeDeadSessionGrace - time.Second)
	if _, err := cleanDeadNativeSessions(runtime); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(oldWorktree); err != nil {
		t.Fatalf("worktree was removed before grace expiry: %v", err)
	}

	runtime.Now = runtime.Now.Add(time.Second)
	if _, err := cleanDeadNativeSessions(runtime); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(oldWorktree); !os.IsNotExist(err) {
		t.Fatalf("expired worktree remains: %v", err)
	}
	if output := testGit(t, repository, "branch", "--list", oldBranch); output != "" {
		t.Fatalf("expired branch remains: %s", output)
	}
	if _, err := os.Stat(leasePath); !os.IsNotExist(err) {
		t.Fatalf("expired lease remains: %v", err)
	}
}

func TestDeadSessionGraceSurvivesDueFleetSweep(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}
	leasePath, lease := onlyNativeLease(t, runtime)
	worktree := lease.Artifacts[0].Worktree
	branch := lease.Artifacts[0].Branch
	lease.PID = 0
	lease.ProcessStart = ""
	if err := writeNativeJSON(leasePath, lease); err != nil {
		t.Fatal(err)
	}
	runtime.Now = runtime.Now.Add(nativeSweepInterval)

	if _, err := prepareNativeLaunch(runtime, "claude"); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(worktree); err != nil {
		t.Fatalf("grace-period worktree was removed by fleet sweep: %v", err)
	}
	if output := testGit(t, repository, "branch", "--list", branch); output == "" {
		t.Fatal("grace-period branch was removed by fleet sweep")
	}
	var retained nativeLease
	if err := readNativeJSON(leasePath, &retained); err != nil {
		t.Fatal(err)
	}
	if retained.DeadSince == nil || !retained.DeadSince.Equal(runtime.Now) {
		t.Fatalf("dead since = %v, want %s", retained.DeadSince, runtime.Now)
	}
}

func TestLiveNativeSessionIsNotCleaned(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}
	leasePath, lease := onlyNativeLease(t, runtime)
	deadSince := runtime.Now.Add(-nativeDeadSessionGrace)
	lease.DeadSince = &deadSince
	if err := writeNativeJSON(leasePath, lease); err != nil {
		t.Fatal(err)
	}

	live, err := cleanDeadNativeSessions(runtime)
	if err != nil {
		t.Fatal(err)
	}

	if !live.contains(lease.Artifacts[0].Worktree) {
		t.Fatal("live worktree was not leased")
	}
	if _, err := os.Stat(lease.Artifacts[0].Worktree); err != nil {
		t.Fatalf("live worktree was removed: %v", err)
	}
	var restored nativeLease
	if err := readNativeJSON(leasePath, &restored); err != nil {
		t.Fatal(err)
	}
	if restored.DeadSince != nil {
		t.Fatalf("live lease kept stale dead since %s", restored.DeadSince)
	}
}

func TestNativeSweepPreservesLiveWorktreeAcrossPathAlias(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if err := os.MkdirAll(runtime.SessionsRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	aliasRoot := filepath.Join(root, "sessions-alias")
	if err := os.Symlink(runtime.SessionsRoot, aliasRoot); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}
	leasePath, lease := onlyNativeLease(t, runtime)
	active := lease.Artifacts[0]
	relative, err := filepath.Rel(runtime.SessionsRoot, active.Worktree)
	if err != nil {
		t.Fatal(err)
	}
	lease.Artifacts[0].Worktree = filepath.Join(aliasRoot, relative)
	if !samePath(active.Worktree, lease.Artifacts[0].Worktree) {
		t.Fatal("lease alias does not resolve to the active worktree")
	}
	if filepath.Clean(active.Worktree) == filepath.Clean(lease.Artifacts[0].Worktree) {
		t.Fatal("lease alias is not textually distinct from the active worktree")
	}
	if err := writeNativeJSON(leasePath, lease); err != nil {
		t.Fatal(err)
	}

	controlBranch := "inactive-control"
	control := filepath.Join(root, "inactive-control")
	testGit(t, repository, "worktree", "add", "-b", controlBranch, control, "origin/main")
	testGit(t, control, "push", "-u", "origin", controlBranch)
	runtime.Now = runtime.Now.Add(nativeSweepInterval)

	if _, err := prepareNativeLaunch(runtime, "claude"); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(active.Worktree); err != nil {
		t.Fatalf("live worktree was removed through its path alias: %v", err)
	}
	if output := testGit(t, repository, "branch", "--list", active.Branch); output == "" {
		t.Fatal("live worktree branch was removed")
	}
	if _, err := os.Stat(control); !os.IsNotExist(err) {
		t.Fatalf("inactive control worktree remains: %v", err)
	}
	if output := testGit(t, repository, "branch", "--list", controlBranch); output != "" {
		t.Fatalf("inactive control branch remains: %s", output)
	}
}

func TestNativeLiveWorktreesFailClosedWhenPathIdentityIsUncertain(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "missing")
	if (nativeLiveWorktrees{}).contains(missing) {
		t.Fatal("empty live set preserved an unrelated missing path")
	}
	live := nativeLiveWorktrees{}
	live.add(missing)

	if !live.contains(t.TempDir()) {
		t.Fatal("uncertain live path allowed workspace cleanup")
	}
}

func TestUnreadableNativeLeaseFailsClosed(t *testing.T) {
	runtime := nativeTestRuntime(t, t.TempDir())
	leasePath := nativeStatePath(runtime, "leases", "unreadable.json")
	if err := os.MkdirAll(filepath.Dir(leasePath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(leasePath, []byte("not JSON\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	live, err := cleanDeadNativeSessions(runtime)
	if err != nil {
		t.Fatal(err)
	}
	if !live.contains(t.TempDir()) {
		t.Fatal("unreadable lease allowed workspace cleanup")
	}
}

func TestExpiredDeadSessionPreservesDirtyWorktree(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}
	leasePath, lease := onlyNativeLease(t, runtime)
	worktree := lease.Artifacts[0].Worktree
	if err := os.WriteFile(filepath.Join(worktree, "unfinished.txt"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	lease.PID = 0
	lease.ProcessStart = ""
	deadSince := runtime.Now.Add(-nativeDeadSessionGrace)
	lease.DeadSince = &deadSince
	if err := writeNativeJSON(leasePath, lease); err != nil {
		t.Fatal(err)
	}

	if _, err := cleanDeadNativeSessions(runtime); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(filepath.Join(worktree, "unfinished.txt")); err != nil {
		t.Fatalf("dirty worktree was removed: %v", err)
	}
}

func TestExpiredDeadSessionPreservesUnpushedWorktree(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}
	leasePath, lease := onlyNativeLease(t, runtime)
	worktree := lease.Artifacts[0].Worktree
	testGit(t, worktree, "config", "user.email", "test@example.com")
	testGit(t, worktree, "config", "user.name", "AOS Test")
	if err := os.WriteFile(filepath.Join(worktree, "local.txt"), []byte("local\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	testGit(t, worktree, "add", "local.txt")
	testGit(t, worktree, "commit", "-m", "local only")
	lease.PID = 0
	lease.ProcessStart = ""
	deadSince := runtime.Now.Add(-nativeDeadSessionGrace)
	lease.DeadSince = &deadSince
	if err := writeNativeJSON(leasePath, lease); err != nil {
		t.Fatal(err)
	}

	if _, err := cleanDeadNativeSessions(runtime); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Stat(worktree); err != nil {
		t.Fatalf("unpushed worktree was removed: %v", err)
	}
}

func TestNativeSweepReturnsExpectedCheckoutToMain(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	testGit(t, repository, "switch", "-c", "task")
	if err := os.WriteFile(filepath.Join(repository, "task.txt"), []byte("done\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", "task.txt")
	testGit(t, repository, "commit", "-m", "task")
	testGit(t, repository, "push", "-u", "origin", "task")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")

	if err := normalizeNativeRepository(runtime, nativeRepository{
		Owner: "owner", Name: "one", Path: repository,
	}, nativeLiveWorktrees{}); err != nil {
		t.Fatal(err)
	}

	if branch := testGit(t, repository, "branch", "--show-current"); branch != "main" {
		t.Fatalf("branch = %s, want main", branch)
	}
	if output := testGit(t, repository, "branch", "--list", "task"); output != "" {
		t.Fatalf("task branch remains: %s", output)
	}
}

func TestNativeSweepReclaimsMainBeforeSwitchingCanonicalCheckout(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	testGit(t, repository, "switch", "-c", "task")
	testGit(t, repository, "push", "-u", "origin", "task")
	mainWorktree := filepath.Join(root, "main-worktree")
	testGit(t, repository, "worktree", "add", mainWorktree, "main")
	runtime := nativeTestRuntime(t, root)

	if err := normalizeNativeRepository(runtime, nativeRepository{
		Owner: "owner", Name: "one", Path: repository,
	}, nativeLiveWorktrees{}); err != nil {
		t.Fatal(err)
	}

	if branch := testGit(t, repository, "branch", "--show-current"); branch != "main" {
		t.Fatalf("branch = %s, want main", branch)
	}
	if _, err := os.Stat(mainWorktree); !os.IsNotExist(err) {
		t.Fatalf("main worktree remains: %v", err)
	}
}

func TestUnexpectedCloneDeletedOnThirdSweep(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "extra")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile)
	writeNativeTestList(t, runtime.FleetFile, "owner")
	expected := nativeExpected{
		Full:      map[string]bool{},
		FleetOrgs: map[string]bool{"owner": true},
	}
	if eligible, _ := unexpectedCloneEligible(
		runtime,
		nativeRepository{Owner: "owner", Name: "extra", Path: repository},
		nativeLiveWorktrees{},
		expected.FleetOrgs,
	); !eligible {
		t.Fatal("clean unexpected clone was not eligible")
	}
	state := nativeSweepState{
		Format: "agentic-os.native-sweep.v1", Candidates: map[string]nativeCandidate{},
	}

	for scan := 1; scan <= 3; scan++ {
		runtime.Now = runtime.Now.Add(nativeSweepInterval)
		if err := runNativeWorkspaceSweep(
			runtime, nil, expected, nativeLiveWorktrees{}, state,
		); err != nil {
			t.Fatal(err)
		}
		_ = readNativeJSON(nativeStatePath(runtime, "sweep.json"), &state)
		if scan < 3 {
			if _, err := os.Stat(repository); err != nil {
				t.Fatalf("repository removed on scan %d: %v", scan, err)
			}
		}
	}
	if _, err := os.Stat(repository); !os.IsNotExist(err) {
		t.Fatalf("repository remains after third scan: %v", err)
	}
}

func TestUnexpectedCloneCounterResetsWhenStateChanges(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "extra")
	runtime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, runtime.PlanFile)
	writeNativeTestList(t, runtime.FleetFile, "owner")
	expected := nativeExpected{
		Full:      map[string]bool{},
		FleetOrgs: map[string]bool{"owner": true},
	}
	state := nativeSweepState{
		Format: "agentic-os.native-sweep.v1", Candidates: map[string]nativeCandidate{},
	}

	runtime.Now = runtime.Now.Add(nativeSweepInterval)
	if err := runNativeWorkspaceSweep(runtime, nil, expected, nativeLiveWorktrees{}, state); err != nil {
		t.Fatal(err)
	}
	state = nativeSweepState{}
	if err := readNativeJSON(nativeStatePath(runtime, "sweep.json"), &state); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(repository, "untracked.txt"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runtime.Now = runtime.Now.Add(nativeSweepInterval)
	if err := runNativeWorkspaceSweep(runtime, nil, expected, nativeLiveWorktrees{}, state); err != nil {
		t.Fatal(err)
	}
	state = nativeSweepState{}
	if err := readNativeJSON(nativeStatePath(runtime, "sweep.json"), &state); err != nil {
		t.Fatal(err)
	}
	if len(state.Candidates) != 0 {
		t.Fatalf("candidate survived changed state: %#v", state.Candidates)
	}
	if err := os.Remove(filepath.Join(repository, "untracked.txt")); err != nil {
		t.Fatal(err)
	}
	runtime.Now = runtime.Now.Add(nativeSweepInterval)
	if err := runNativeWorkspaceSweep(runtime, nil, expected, nativeLiveWorktrees{}, state); err != nil {
		t.Fatal(err)
	}
	state = nativeSweepState{}
	if err := readNativeJSON(nativeStatePath(runtime, "sweep.json"), &state); err != nil {
		t.Fatal(err)
	}
	if candidate := state.Candidates[repository]; candidate.Scans != 1 {
		t.Fatalf("candidate count = %d, want reset to 1", candidate.Scans)
	}
}

func TestNativeSweepCacheIsFreshForTenMinutes(t *testing.T) {
	root := t.TempDir()
	runtime := nativeTestRuntime(t, root)
	state := nativeSweepState{
		Format: "agentic-os.native-sweep.v1", LastSweep: runtime.Now,
		Candidates: map[string]nativeCandidate{},
	}
	if err := writeNativeJSON(nativeStatePath(runtime, "sweep.json"), state); err != nil {
		t.Fatal(err)
	}

	runtime.Now = runtime.Now.Add(nativeSweepInterval - time.Second)
	if due, _ := nativeSweepDue(runtime); due {
		t.Fatal("sweep became due before ten minutes")
	}
	runtime.Now = runtime.Now.Add(time.Second)
	if due, _ := nativeSweepDue(runtime); !due {
		t.Fatal("sweep was not due at ten minutes")
	}
}

func TestOriginOwner(t *testing.T) {
	for remote, want := range map[string]string{
		"https://forge.example/owner/repo.git": "owner",
		"ssh://git@forge.example/owner/repo":   "owner",
		"git@forge.example:owner/repo.git":     "owner",
	} {
		if got := originOwner(remote); got != want {
			t.Errorf("originOwner(%q) = %q, want %q", remote, got, want)
		}
	}
}

func TestHumanWorkdirIsOutsideAutomation(t *testing.T) {
	if !humanWorkdir("/tmp/infrastructure-workdir") {
		t.Fatal("human workdir was not recognized")
	}
	if humanWorkdir("/tmp/infrastructure-agent") {
		t.Fatal("ordinary worktree was recognized as human workdir")
	}
}

func TestNativeGitOperationInProgressUsesRepositoryRelativePath(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	gitDirectory := testGit(t, repository, "rev-parse", "--git-dir")
	if !filepath.IsAbs(gitDirectory) {
		gitDirectory = filepath.Join(repository, gitDirectory)
	}
	if err := os.WriteFile(filepath.Join(gitDirectory, "MERGE_HEAD"), []byte("test\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	inProgress, err := nativeGitOperationInProgress(repository)
	if err != nil {
		t.Fatal(err)
	}
	if !inProgress {
		t.Fatal("relative Git operation marker was not detected")
	}
}
