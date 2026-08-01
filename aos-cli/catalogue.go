package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const (
	defaultCatalogueTTL  = 10 * time.Minute
	defaultCataloguePath = ".agents/skills"
)

type catalogueSource struct {
	Locator     string
	URL         string
	Revision    string
	CatalogPath string
}

type catalogueHydrateOptions struct {
	StateDir string
	TTL      time.Duration
	Now      func() time.Time
	Check    bool
}

type hydratedCatalogue struct {
	Source  catalogueSource
	Path    string
	Commit  string
	State   string
	Warning string
}

func parseCatalogueLocator(raw string) (catalogueSource, error) {
	locator := strings.TrimSpace(raw)
	if locator == "" {
		return catalogueSource{}, fmt.Errorf("catalogue source locator cannot be empty")
	}
	address, revision := splitCatalogueRevision(locator)
	repository, catalogPath, err := splitCatalogueRepositoryPath(address)
	if err != nil {
		return catalogueSource{}, err
	}
	source := catalogueSource{
		Locator:     locator,
		URL:         repository,
		Revision:    revision,
		CatalogPath: catalogPath,
	}
	if err := validateCatalogueSource(source); err != nil {
		return catalogueSource{}, err
	}
	return source, nil
}

func splitCatalogueRevision(locator string) (string, string) {
	index := strings.LastIndex(locator, "@")
	if index < 0 || catalogueAtIsURLUser(locator, index) {
		return locator, "HEAD"
	}
	revision := strings.TrimSpace(locator[index+1:])
	if revision == "" {
		return locator[:index], ""
	}
	return locator[:index], revision
}

func catalogueAtIsURLUser(locator string, index int) bool {
	if scheme := strings.Index(locator, "://"); scheme >= 0 {
		authority := locator[scheme+3:]
		if slash := strings.Index(authority, "/"); slash >= 0 {
			return index < scheme+3+slash
		}
		return true
	}
	return !strings.Contains(locator[:index], "/") &&
		strings.Contains(locator[index+1:], ":")
}

func splitCatalogueRepositoryPath(address string) (string, string, error) {
	address = strings.TrimSpace(address)
	if address == "" {
		return "", "", fmt.Errorf("catalogue source needs a repository")
	}
	if marker := strings.LastIndex(address, ".git/"); marker >= 0 {
		repository := address[:marker+len(".git")]
		catalogPath := address[marker+len(".git/"):]
		clean, err := cleanCataloguePath(catalogPath)
		return repository, clean, err
	}
	if strings.HasSuffix(address, ".git") ||
		strings.Contains(address, "://") ||
		strings.HasPrefix(address, "/") ||
		strings.HasPrefix(address, "./") ||
		strings.HasPrefix(address, "../") ||
		strings.Contains(address, `\`) ||
		strings.Contains(address, ":") {
		return address, defaultCataloguePath, nil
	}
	parts := strings.Split(strings.Trim(address, "/"), "/")
	if len(parts) < 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf(
			"catalogue source %q must use owner/repo/path@ref or a Git URL",
			address,
		)
	}
	ownerIndex := 0
	if parts[0] == "github.com" {
		if len(parts) < 3 {
			return "", "", fmt.Errorf(
				"catalogue source %q needs a GitHub owner and repository",
				address,
			)
		}
		ownerIndex = 1
	}
	repository := "https://github.com/" +
		parts[ownerIndex] + "/" + parts[ownerIndex+1] + ".git"
	catalogPath := defaultCataloguePath
	if len(parts) > ownerIndex+2 {
		var err error
		catalogPath, err = cleanCataloguePath(
			strings.Join(parts[ownerIndex+2:], "/"),
		)
		if err != nil {
			return "", "", err
		}
	}
	return repository, catalogPath, nil
}

func cleanCataloguePath(catalogPath string) (string, error) {
	if strings.TrimSpace(catalogPath) == "" {
		return "", fmt.Errorf("catalogue source path cannot be empty")
	}
	clean := path.Clean(catalogPath)
	if strings.HasPrefix(catalogPath, "/") ||
		clean == "." ||
		clean == ".." ||
		strings.HasPrefix(clean, "../") {
		return "", fmt.Errorf(
			"catalogue source path %q must stay inside its repository",
			catalogPath,
		)
	}
	return clean, nil
}

func validateCatalogueSource(source catalogueSource) error {
	if strings.TrimSpace(source.URL) == "" {
		return fmt.Errorf("catalogue source needs a URL")
	}
	if strings.TrimSpace(source.Revision) == "" {
		return fmt.Errorf("catalogue source %q needs a revision", source.Locator)
	}
	if _, err := cleanCataloguePath(source.CatalogPath); err != nil {
		return err
	}
	if parsed, err := url.Parse(source.URL); err == nil && parsed.User != nil {
		return fmt.Errorf("catalogue source %q must not embed credentials", source.Locator)
	}
	return nil
}

func hydrateCatalogues(
	ctx context.Context,
	sources []catalogueSource,
	opts catalogueHydrateOptions,
) ([]hydratedCatalogue, bool, error) {
	results := make([]hydratedCatalogue, 0, len(sources))
	drift := false
	for _, source := range sources {
		var result hydratedCatalogue
		var itemDrift bool
		var err error
		if opts.Check {
			result, itemDrift, err = inspectCatalogue(ctx, source, opts)
		} else {
			result, err = hydrateCatalogue(ctx, source, opts)
		}
		if err != nil {
			return nil, false, err
		}
		results = append(results, result)
		drift = drift || itemDrift
	}
	return results, drift, nil
}

func hydrateCatalogue(
	ctx context.Context,
	source catalogueSource,
	opts catalogueHydrateOptions,
) (hydratedCatalogue, error) {
	cacheRoot := catalogueCacheRoot(opts.StateDir, source)
	mirror := filepath.Join(cacheRoot, "mirror.git")
	work := filepath.Join(cacheRoot, "work")
	if err := os.MkdirAll(cacheRoot, 0o755); err != nil {
		return hydratedCatalogue{}, fmt.Errorf("create catalogue cache: %w", err)
	}
	unlock, err := lockCatalogueCache(cacheRoot)
	if err != nil {
		return hydratedCatalogue{}, err
	}
	defer unlock()

	state := "cached"
	warning := ""
	if !isDirectory(mirror) {
		if err := cloneCatalogueMirror(ctx, source.URL, mirror, opts.Now()); err != nil {
			return hydratedCatalogue{}, fmt.Errorf(
				"hydrate catalogue source %s: %w",
				source.Locator,
				err,
			)
		}
		state = "hydrated"
	} else if catalogueMirrorStale(mirror, opts.TTL, opts.Now()) {
		if immutableCatalogueRefPresent(ctx, mirror, source.Revision) {
			touchCatalogueFetchHead(mirror, opts.Now())
		} else if err := runCatalogueGit(ctx, "-C", mirror, "remote", "update", "--prune"); err != nil {
			state = "fallback"
			warning = fmt.Sprintf(
				"catalogue refresh failed for %s, using verified cache: %v",
				source.Locator,
				err,
			)
			if checkoutCatalogueValid(work, source.CatalogPath) {
				commit, resolveErr := resolveCatalogueCommit(ctx, work, "HEAD")
				if resolveErr != nil {
					return hydratedCatalogue{}, resolveErr
				}
				return hydratedCatalogue{
					Source:  source,
					Path:    filepath.Join(work, filepath.FromSlash(source.CatalogPath)),
					Commit:  commit,
					State:   state,
					Warning: warning,
				}, nil
			}
		} else {
			touchCatalogueFetchHead(mirror, opts.Now())
			state = "refreshed"
		}
	}
	return materializeCatalogue(ctx, source, mirror, work, state, warning)
}

func inspectCatalogue(
	ctx context.Context,
	source catalogueSource,
	opts catalogueHydrateOptions,
) (hydratedCatalogue, bool, error) {
	cacheRoot := catalogueCacheRoot(opts.StateDir, source)
	mirror := filepath.Join(cacheRoot, "mirror.git")
	work := filepath.Join(cacheRoot, "work")
	if !isDirectory(mirror) {
		return hydratedCatalogue{
			Source: source,
			Path: filepath.Join(
				work,
				filepath.FromSlash(source.CatalogPath),
			),
			State: "missing",
		}, true, nil
	}
	commit, err := resolveCatalogueCommit(ctx, mirror, source.Revision)
	if err != nil {
		return hydratedCatalogue{}, true, fmt.Errorf(
			"resolve cached catalogue source %s: %w",
			source.Locator,
			err,
		)
	}
	if err := verifyCatalogueTree(ctx, mirror, source.Revision, source.CatalogPath); err != nil {
		return hydratedCatalogue{}, true, fmt.Errorf(
			"verify cached catalogue source %s: %w",
			source.Locator,
			err,
		)
	}
	checkoutCurrent := checkoutCatalogueMatches(ctx, work, commit, source.CatalogPath)
	staleMutable := catalogueMirrorStale(mirror, opts.TTL, opts.Now()) &&
		!immutableCatalogueRefPresent(ctx, mirror, source.Revision)
	return hydratedCatalogue{
		Source: source,
		Path:   filepath.Join(work, filepath.FromSlash(source.CatalogPath)),
		Commit: commit,
		State:  "cached",
	}, !checkoutCurrent || staleMutable, nil
}

func materializeCatalogue(
	ctx context.Context,
	source catalogueSource,
	mirror string,
	work string,
	state string,
	warning string,
) (hydratedCatalogue, error) {
	commit, err := resolveCatalogueCommit(ctx, mirror, source.Revision)
	if err != nil {
		return hydratedCatalogue{}, fmt.Errorf(
			"resolve catalogue source %s: %w",
			source.Locator,
			err,
		)
	}
	if err := verifyCatalogueTree(ctx, mirror, source.Revision, source.CatalogPath); err != nil {
		return hydratedCatalogue{}, fmt.Errorf(
			"resolve catalogue source %s: %w",
			source.Locator,
			err,
		)
	}
	if !checkoutCatalogueMatches(ctx, work, commit, source.CatalogPath) {
		if err := replaceCatalogueCheckout(ctx, source, mirror, work, commit); err != nil {
			return hydratedCatalogue{}, fmt.Errorf(
				"materialize catalogue source %s: %w",
				source.Locator,
				err,
			)
		}
	}
	return hydratedCatalogue{
		Source:  source,
		Path:    filepath.Join(work, filepath.FromSlash(source.CatalogPath)),
		Commit:  commit,
		State:   state,
		Warning: warning,
	}, nil
}

func catalogueCacheRoot(stateDir string, source catalogueSource) string {
	hash := sha256.New()
	fmt.Fprintf(
		hash,
		"url\x00%s\x00revision\x00%s\x00path\x00%s\x00",
		source.URL,
		source.Revision,
		source.CatalogPath,
	)
	key := hex.EncodeToString(hash.Sum(nil))
	return filepath.Join(stateDir, "cache", "catalogues", key)
}

func cloneCatalogueMirror(ctx context.Context, remote, mirror string, now time.Time) error {
	parent := filepath.Dir(mirror)
	stage, err := os.MkdirTemp(parent, ".mirror-*")
	if err != nil {
		return err
	}
	if err := os.Remove(stage); err != nil {
		return err
	}
	defer os.RemoveAll(stage)
	if err := runCatalogueGit(ctx, "clone", "--mirror", remote, stage); err != nil {
		return err
	}
	touchCatalogueFetchHead(stage, now)
	return os.Rename(stage, mirror)
}

func resolveCatalogueCommit(ctx context.Context, repository, revision string) (string, error) {
	target := revision + "^{commit}"
	output, err := catalogueGitOutput(
		ctx,
		"-C",
		repository,
		"rev-parse",
		"--verify",
		target,
	)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(output), nil
}

func verifyCatalogueTree(
	ctx context.Context,
	mirror string,
	revision string,
	catalogPath string,
) error {
	objectType, err := catalogueGitOutput(
		ctx,
		"-C",
		mirror,
		"cat-file",
		"-t",
		revision+":"+catalogPath,
	)
	if err != nil {
		return err
	}
	if strings.TrimSpace(objectType) != "tree" {
		return fmt.Errorf("catalogue path %q is not a directory", catalogPath)
	}
	return nil
}

func checkoutCatalogueMatches(
	ctx context.Context,
	work string,
	commit string,
	catalogPath string,
) bool {
	if !checkoutCatalogueValid(work, catalogPath) {
		return false
	}
	output, err := catalogueGitOutput(
		ctx,
		"-C",
		work,
		"rev-parse",
		"--verify",
		"HEAD^{commit}",
	)
	return err == nil && strings.TrimSpace(output) == commit
}

func checkoutCatalogueValid(work, catalogPath string) bool {
	return isDirectory(filepath.Join(work, ".git")) &&
		isDirectory(filepath.Join(work, filepath.FromSlash(catalogPath)))
}

func replaceCatalogueCheckout(
	ctx context.Context,
	source catalogueSource,
	mirror string,
	work string,
	commit string,
) error {
	parent := filepath.Dir(work)
	stage, err := os.MkdirTemp(parent, ".work-*")
	if err != nil {
		return err
	}
	if err := os.Remove(stage); err != nil {
		return err
	}
	defer os.RemoveAll(stage)
	if err := runCatalogueGit(ctx, "clone", "--quiet", mirror, stage); err != nil {
		return err
	}
	if err := runCatalogueGit(
		ctx,
		"-C",
		stage,
		"remote",
		"set-url",
		"origin",
		source.URL,
	); err != nil {
		return err
	}
	if err := runCatalogueGit(
		ctx,
		"-C",
		stage,
		"-c",
		"advice.detachedHead=false",
		"checkout",
		"--quiet",
		commit,
	); err != nil {
		return err
	}
	if !isDirectory(filepath.Join(stage, filepath.FromSlash(source.CatalogPath))) {
		return fmt.Errorf("catalogue path %q is not a directory", source.CatalogPath)
	}
	return swapCatalogueCheckout(stage, work)
}

func swapCatalogueCheckout(stage, work string) error {
	backup := work + ".previous"
	if !isDirectory(work) && isDirectory(backup) {
		if err := os.Rename(backup, work); err != nil {
			return err
		}
	}
	_ = os.RemoveAll(backup)
	hadWork := isDirectory(work)
	if hadWork {
		if err := os.Rename(work, backup); err != nil {
			return err
		}
	}
	if err := os.Rename(stage, work); err != nil {
		if hadWork {
			_ = os.Rename(backup, work)
		}
		return err
	}
	_ = os.RemoveAll(backup)
	return nil
}

var fullCatalogueSHA = regexp.MustCompile(`^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$`)

func immutableCatalogueRefPresent(ctx context.Context, mirror, revision string) bool {
	if !fullCatalogueSHA.MatchString(revision) {
		return false
	}
	return runCatalogueGit(ctx, "-C", mirror, "cat-file", "-e", revision+"^{commit}") == nil
}

func catalogueMirrorStale(mirror string, ttl time.Duration, now time.Time) bool {
	info, err := os.Stat(filepath.Join(mirror, "FETCH_HEAD"))
	if err != nil {
		return true
	}
	return now.Sub(info.ModTime()) >= ttl
}

func touchCatalogueFetchHead(mirror string, now time.Time) {
	fetchHead := filepath.Join(mirror, "FETCH_HEAD")
	if err := os.Chtimes(fetchHead, now, now); err != nil {
		_ = os.WriteFile(fetchHead, nil, 0o644)
		_ = os.Chtimes(fetchHead, now, now)
	}
}

func isDirectory(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

func runCatalogueGit(ctx context.Context, args ...string) error {
	_, err := catalogueGitOutput(ctx, args...)
	return err
}

func catalogueGitOutput(ctx context.Context, args ...string) (string, error) {
	command := exec.CommandContext(ctx, "git", args...)
	raw, err := command.CombinedOutput()
	if err != nil {
		message := strings.TrimSpace(string(raw))
		if message == "" {
			return "", err
		}
		return "", fmt.Errorf("%w: %s", err, message)
	}
	return string(raw), nil
}
