package main

import (
	"crypto/sha256"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strings"
)

// The v1 JSON plan seals no provenance, so a launch reading one verifies
// nothing. docs/native-session-start.md
const legacyRepositoryPlanRemoval = "2026-10-01"

// planProvenanceMismatch names which policy source disagreed, so the stop says
// what moved rather than that something did.
type planProvenanceMismatch struct {
	Identity string
	Reason   string
}

func (mismatch planProvenanceMismatch) String() string {
	return mismatch.Identity + ": " + mismatch.Reason
}

// runPlanRegeneration is the seam tests replace. Regenerating for real shells
// out, so a test that leaves this alone would reach the host's Agent Compose.
var runPlanRegeneration = regenerateRepositoryPlan

// verifiedRepositoryPlan regenerates exactly once when the sealed provenance
// disagrees, then stops the launch. docs/native-session-start.md
func verifiedRepositoryPlan(runtime nativeRuntime) (aosRepositoryPlan, error) {
	plan, err := loadAOSRepositoryPlan(runtime.PlanFile)
	if err != nil {
		return aosRepositoryPlan{}, err
	}
	if plan.Legacy {
		fmt.Fprintf(runtime.Stderr,
			"aos: %s is the deprecated %s format, which seals no provenance and is removed after %s. Run agent-compose compose to write %s.\n",
			runtime.PlanFile, agentComposeRepositoryPlanJSONFormat,
			legacyRepositoryPlanRemoval, agentComposeRepositoryPlanYAMLFormat)
		return plan, nil
	}
	if len(plan.Inputs) == 0 {
		fmt.Fprintf(runtime.Stderr,
			"aos: %s seals no policy inputs, so its provenance cannot be verified\n",
			runtime.PlanFile)
		plan.Unverified = true
		return plan, nil
	}
	if len(verifyPlanProvenance(runtime, plan)) == 0 {
		return plan, nil
	}
	return refreshedRepositoryPlan(runtime, plan), nil
}

// refreshedRepositoryPlan keeps the plan current without ever being a wall.
// See docs/native-session-start.md.
func refreshedRepositoryPlan(runtime nativeRuntime, loaded aosRepositoryPlan) aosRepositoryPlan {
	if err := runPlanRegeneration(runtime); err != nil {
		// Silent on the happy path, but a refresh that cannot run leaves the
		// plan stale for every later launch, which is worth one line.
		fmt.Fprintf(runtime.Stderr, "aos: could not refresh the repository plan: %v\n", err)
		return loaded
	}
	plan, err := loadAOSRepositoryPlan(runtime.PlanFile)
	if err != nil || plan.Legacy || len(plan.Inputs) == 0 {
		return loaded
	}
	return plan
}

func verifyPlanProvenance(
	runtime nativeRuntime,
	plan aosRepositoryPlan,
) []planProvenanceMismatch {
	mismatches := make([]planProvenanceMismatch, 0)
	for _, input := range plan.Inputs {
		owner, name, ok := strings.Cut(input.Identity, "/")
		if !ok || !safePathSegment(owner) || !safePathSegment(name) {
			mismatches = append(mismatches, planProvenanceMismatch{
				Identity: input.Identity, Reason: "sealed identity is not owner/name",
			})
			continue
		}
		checkout := filepath.Join(runtime.ProjectsRoot, owner, name)
		policy, ok := policySourcePath(checkout, input.Policy.Path)
		if !ok {
			mismatches = append(mismatches, planProvenanceMismatch{
				Identity: input.Identity,
				Reason:   fmt.Sprintf("sealed policy path %q escapes the checkout", input.Policy.Path),
			})
			continue
		}
		fetchPolicySource(runtime, input.Identity, checkout)
		digest, err := fileDigest(policy)
		if err != nil {
			mismatches = append(mismatches, planProvenanceMismatch{
				Identity: input.Identity, Reason: err.Error(),
			})
			continue
		}
		if digest != input.Policy.SHA256 {
			mismatches = append(mismatches, planProvenanceMismatch{
				Identity: input.Identity,
				Reason: fmt.Sprintf("%s is %s, sealed as %s",
					input.Policy.Path, digest, input.Policy.SHA256),
			})
			continue
		}
		if reason, ok := policyBaseMismatch(checkout, input); !ok {
			mismatches = append(mismatches, planProvenanceMismatch{
				Identity: input.Identity, Reason: reason,
			})
			continue
		}
		reportPolicyRevisionDrift(runtime, input, checkout)
	}
	return mismatches
}

// The session reads policy from the worktree base, not from the checkout Agent
// Compose hashed. docs/native-session-start.md
func policyBaseMismatch(checkout string, input aosRepositoryPlanInput) (string, bool) {
	if _, err := os.Stat(filepath.Join(checkout, ".git")); err != nil {
		return "", true
	}
	// nativeGit trims, and a trailing newline is part of what was hashed.
	command := exec.Command("git", "-C", checkout, "cat-file", "blob",
		nativeWorktreeBase+":"+path.Clean(strings.TrimSpace(input.Policy.Path)))
	command.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0")
	blob, err := command.Output()
	if err != nil {
		return "", true
	}
	digest := fmt.Sprintf("sha256:%x", sha256.Sum256(blob))
	if digest == input.Policy.SHA256 {
		return "", true
	}
	return fmt.Sprintf("%s at %s does not match the sealed digest, so pull %s before launching",
		input.Policy.Path, nativeWorktreeBase, input.Identity), false
}

func policySourcePath(checkout, relative string) (string, bool) {
	cleaned := filepath.Clean(filepath.FromSlash(strings.TrimSpace(relative)))
	if cleaned == "" || cleaned == "." || filepath.IsAbs(cleaned) ||
		cleaned == ".." || strings.HasPrefix(cleaned, ".."+string(filepath.Separator)) {
		return "", false
	}
	return filepath.Join(checkout, cleaned), true
}

// A laptop off the network still launches: the fetch warns and the digest
// comparison stays the gate.
func fetchPolicySource(runtime nativeRuntime, identity, checkout string) {
	if _, err := os.Stat(filepath.Join(checkout, ".git")); err != nil {
		return
	}
	if _, err := nativeGit(checkout, "fetch", "--quiet", "origin"); err != nil {
		fmt.Fprintf(runtime.Stderr,
			"aos: policy source %s not fetched, verifying against the local checkout: %v\n",
			identity, err)
	}
}

// A revision that moved without moving the policy is provenance to refresh at
// the next regeneration, not a reason to stop a launch that is still correct.
func reportPolicyRevisionDrift(
	runtime nativeRuntime,
	input aosRepositoryPlanInput,
	checkout string,
) {
	head, err := nativeGit(checkout, "rev-parse", "HEAD")
	if err != nil || head == input.Revision || input.Revision == "" {
		return
	}
	fmt.Fprintf(runtime.Stderr,
		"aos: policy source %s is at %s, sealed at %s, and %s is unchanged\n",
		input.Identity, shortRevision(head), shortRevision(input.Revision), input.Policy.Path)
}

func shortRevision(revision string) string {
	if len(revision) <= 12 {
		return revision
	}
	return revision[:12]
}

func fileDigest(filename string) (string, error) {
	raw, err := os.ReadFile(filename)
	if errors.Is(err, fs.ErrNotExist) {
		return "", fmt.Errorf("%s is missing", filepath.Base(filename))
	}
	if err != nil {
		return "", fmt.Errorf("read %s: %w", filepath.Base(filename), err)
	}
	return fmt.Sprintf("sha256:%x", sha256.Sum256(raw)), nil
}

// Without Agent Compose the launch cannot converge, and a stale plan must not
// reach worktree creation.
func regenerateRepositoryPlan(runtime nativeRuntime) error {
	binary, err := hostLookPath("agent-compose")
	if err != nil {
		return fmt.Errorf("regeneration needs Agent Compose on PATH: %w", err)
	}
	command := exec.Command(binary, "compose", "--reapply")
	command.Env = append(os.Environ(),
		"HOME="+repositoryPlanHome(runtime.PlanFile, runtime.Home))
	// The converge report is agent-compose talking to itself on a good run, so
	// it is captured for the error rather than forwarded to the operator.
	var report strings.Builder
	command.Stdout = &report
	command.Stderr = &report
	if err := command.Run(); err != nil {
		return fmt.Errorf("agent-compose compose: %w: %s", err,
			strings.TrimSpace(report.String()))
	}
	return nil
}

// A shadow regenerating into its own HOME leaves the canonical plan stale.
// docs/native-session-start.md
func repositoryPlanHome(planFile, fallback string) string {
	directory := filepath.Dir(planFile)
	if filepath.Base(directory) != ".agent-compose" {
		return fallback
	}
	return filepath.Dir(directory)
}
