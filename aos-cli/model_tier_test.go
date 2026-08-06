package main

import "testing"

func TestModelTierForModel(t *testing.T) {
	t.Parallel()
	tests := map[string]string{
		"claude-sonnet-4-6":                  modelTierFrontier,
		"codex":                              modelTierFrontier,
		"gpt-5.6-sol":                        modelTierFrontier,
		"deploy-backend/deepseek-v4-flash":   modelTierCommodity,
		"goose":                              modelTierOSS,
		"opencode":                           modelTierOSS,
		"ornith:35b":                         modelTierOSS,
		"mistral-small3.2:24b":               modelTierOSS,
		"mistralai/Ministral-3-14B-Instruct": modelTierOSS,
		"qwen3.6:35b":                        modelTierOSS,
	}
	for model, want := range tests {
		model, want := model, want
		t.Run(model, func(t *testing.T) {
			t.Parallel()
			got, err := modelTierForModel(model)
			if err != nil {
				t.Fatal(err)
			}
			if got != want {
				t.Fatalf("modelTierForModel(%q) = %q, want %q", model, got, want)
			}
		})
	}
}

func TestModelTierForModelRejectsUnknownModels(t *testing.T) {
	t.Parallel()
	for _, model := range []string{"", "unknown-model"} {
		if _, err := modelTierForModel(model); err == nil {
			t.Fatalf("modelTierForModel(%q) succeeded", model)
		}
	}
}

func TestNativeRuntimeModelUsesHarnessOverride(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		command []string
		want    string
	}{
		{
			name: "long option",
			command: []string{
				"agent-compose", "launch", "engineer", "goose",
				"--model", "deepseek-v4-flash",
			},
			want: "deepseek-v4-flash",
		},
		{
			name: "equals option",
			command: []string{
				"agent-compose", "launch", "community", "goose",
				"--model=ornith:35b",
			},
			want: "ornith:35b",
		},
		{
			name:    "direct harness short option",
			command: []string{"goose", "-m", "ministral-3:14b"},
			want:    "ministral-3:14b",
		},
	}
	for _, test := range tests {
		test := test
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			got, err := nativeRuntimeModel("goose", test.command)
			if err != nil {
				t.Fatal(err)
			}
			if got != test.want {
				t.Fatalf("nativeRuntimeModel() = %q, want %q", got, test.want)
			}
		})
	}
}

func TestNativeRuntimeModelFallsBackToHarness(t *testing.T) {
	t.Parallel()
	got, err := nativeRuntimeModel(
		"goose",
		[]string{"agent-compose", "launch", "community", "goose"},
	)
	if err != nil {
		t.Fatal(err)
	}
	if got != "goose" {
		t.Fatalf("nativeRuntimeModel() = %q, want goose", got)
	}
}

func TestNativeRuntimeModelRejectsMissingOverrideValue(t *testing.T) {
	t.Parallel()
	_, err := nativeRuntimeModel(
		"goose",
		[]string{"agent-compose", "launch", "engineer", "goose", "--model"},
	)
	if err == nil {
		t.Fatal("nativeRuntimeModel accepted --model without a value")
	}
}
