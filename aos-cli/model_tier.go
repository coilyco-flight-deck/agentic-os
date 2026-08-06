package main

import (
	"fmt"
	"path/filepath"
	"strings"
)

const (
	modelTierFrontier  = "frontier"
	modelTierCommodity = "commodity"
	modelTierOSS       = "oss"
)

func modelTierForModel(model string) (string, error) {
	normalized := strings.ToLower(strings.TrimSpace(model))
	if normalized == "" {
		return "", fmt.Errorf("runtime model is empty")
	}

	switch {
	case strings.Contains(normalized, "deepseek"):
		return modelTierCommodity, nil
	case strings.Contains(normalized, "claude"),
		strings.Contains(normalized, "codex"),
		strings.Contains(normalized, "gpt-"):
		return modelTierFrontier, nil
	case strings.Contains(normalized, "ornith"),
		normalized == "goose",
		normalized == "opencode",
		strings.Contains(normalized, "mistral"),
		strings.Contains(normalized, "ministral"),
		strings.Contains(normalized, "qwen"):
		return modelTierOSS, nil
	default:
		return "", fmt.Errorf("runtime model %q has no AOS model tier", model)
	}
}

func nativeRuntimeModel(harness string, command []string) (string, error) {
	args := nativeHarnessArguments(command, harness)
	model := strings.TrimSpace(harness)
	for index := 0; index < len(args); index++ {
		arg := args[index]
		if arg == "--" {
			break
		}
		switch {
		case arg == "--model" || arg == "-m":
			if index+1 >= len(args) || strings.TrimSpace(args[index+1]) == "" {
				return "", fmt.Errorf("%s needs a value", arg)
			}
			index++
			model = args[index]
		case strings.HasPrefix(arg, "--model="):
			model = strings.TrimPrefix(arg, "--model=")
		case strings.HasPrefix(arg, "-m="):
			model = strings.TrimPrefix(arg, "-m=")
		}
	}
	if strings.TrimSpace(model) == "" {
		return "", fmt.Errorf("native %s runtime model is empty", harness)
	}
	return model, nil
}

func nativeHarnessArguments(command []string, harness string) []string {
	for index, arg := range command {
		base := strings.TrimSuffix(filepath.Base(arg), filepath.Ext(arg))
		if strings.EqualFold(base, harness) {
			return command[index+1:]
		}
	}
	return nil
}
