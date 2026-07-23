package main

import (
	"strings"
	"testing"
)

func TestEmbeddedHarnessBoardResolvesConfirmedDefaults(t *testing.T) {
	t.Parallel()
	board, err := loadHarnessBoard(embeddedHarnessBoard)
	if err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		role    string
		intent  string
		harness string
	}{
		{role: "director", intent: "strategic-planning", harness: "plandex"},
		{role: "customer-success", intent: "knowledge-retrieval", harness: "rasa"},
		{role: "customer-success", intent: "conversation-management", harness: "rasa"},
	} {
		test := test
		t.Run(test.role+"/"+test.intent, func(t *testing.T) {
			t.Parallel()
			got, err := resolveHarnessDefault(board, test.role, test.intent)
			if err != nil {
				t.Fatal(err)
			}
			if got != test.harness {
				t.Fatalf("resolveHarnessDefault() = %q, want %q", got, test.harness)
			}
			if strings.Contains(got, test.role) || strings.Contains(got, test.intent) {
				t.Fatalf("control-plane provenance leaked into harness output %q", got)
			}
		})
	}
}

func TestResolveHarnessDefaultRejectsUnknownLane(t *testing.T) {
	t.Parallel()
	board, err := loadHarnessBoard(embeddedHarnessBoard)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := resolveHarnessDefault(board, "director", "code-review"); err == nil {
		t.Fatal("unknown role-intent lane resolved")
	}
}

func TestHarnessBoardRejectsBackendFields(t *testing.T) {
	t.Parallel()
	data := []byte(`{
		"format": "agentic-os.role-harness-board.v1",
		"role_source": "source",
		"role_count": 1,
		"lane_count": 1,
		"roles": [{
			"role": "engineer",
			"intents": [{
				"intent": "autonomous-coding",
				"harness": "openhands",
				"model": "must-not-cross"
			}]
		}]
	}`)
	if _, err := loadHarnessBoard(data); err == nil {
		t.Fatal("backend model field crossed into the launcher contract")
	}
}
