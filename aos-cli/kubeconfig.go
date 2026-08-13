package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/goccy/go-yaml"
)

type kubeconfigDocument struct {
	APIVersion string                   `json:"apiVersion"`
	Kind       string                   `json:"kind"`
	Clusters   []kubeconfigClusterEntry `json:"clusters"`
	Contexts   []kubeconfigContextEntry `json:"contexts"`
	Users      []kubeconfigUserEntry    `json:"users"`
}

type kubeconfigClusterEntry struct {
	Name    string         `json:"name"`
	Cluster map[string]any `json:"cluster"`
}

type kubeconfigContextEntry struct {
	Name    string         `json:"name"`
	Context map[string]any `json:"context"`
}

type kubeconfigUserEntry struct {
	Name string         `json:"name"`
	User map[string]any `json:"user"`
}

func resolveKubeconfigMount(source string) (string, error) {
	if source == "" {
		return "", nil
	}
	path, err := filepath.Abs(source)
	if err != nil {
		return "", fmt.Errorf("resolve selected kubeconfig %q: %w", source, err)
	}
	info, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return "", fmt.Errorf("selected kubeconfig %q does not exist", path)
		}
		return "", fmt.Errorf("inspect selected kubeconfig %q: %w", path, err)
	}
	if !info.Mode().IsRegular() {
		return "", fmt.Errorf("selected kubeconfig %q is not a regular file", path)
	}
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("read selected kubeconfig %q: %w", path, err)
	}
	defer file.Close()

	decoder := yaml.NewDecoder(file)
	var document kubeconfigDocument
	if err := decoder.Decode(&document); err != nil {
		if err == io.EOF {
			return "", fmt.Errorf("selected kubeconfig %q is malformed: file is empty", path)
		}
		return "", fmt.Errorf("selected kubeconfig %q is malformed: %w", path, err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		if err == nil {
			return "", fmt.Errorf(
				"selected kubeconfig %q is malformed: multiple YAML documents are not supported",
				path,
			)
		}
		return "", fmt.Errorf("selected kubeconfig %q is malformed: %w", path, err)
	}
	if document.APIVersion != "v1" || document.Kind != "Config" {
		return "", fmt.Errorf(
			"selected kubeconfig %q is malformed: want apiVersion v1 and kind Config",
			path,
		)
	}
	for _, entry := range document.Clusters {
		if strings.TrimSpace(entry.Name) == "" || entry.Cluster == nil {
			return "", fmt.Errorf(
				"selected kubeconfig %q is malformed: every cluster needs a name and mapping",
				path,
			)
		}
	}
	for _, entry := range document.Contexts {
		if strings.TrimSpace(entry.Name) == "" || entry.Context == nil {
			return "", fmt.Errorf(
				"selected kubeconfig %q is malformed: every context needs a name and mapping",
				path,
			)
		}
	}
	for _, entry := range document.Users {
		if strings.TrimSpace(entry.Name) == "" || entry.User == nil {
			return "", fmt.Errorf(
				"selected kubeconfig %q is malformed: every user needs a name and mapping",
				path,
			)
		}
	}
	return path, nil
}
