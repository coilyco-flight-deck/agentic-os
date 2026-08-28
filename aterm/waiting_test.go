package main

import (
	"bytes"
	"strings"
	"testing"
	"time"
)

func TestAFastCallNeverAnnouncesItself(t *testing.T) {
	notice := &bytes.Buffer{}
	got := whileWaiting(notice, []string{"aos", "_launch-agent", "advocate"}, func() string {
		return "claude"
	})
	if got != "claude" {
		t.Fatalf("call returned %q", got)
	}
	if notice.Len() != 0 {
		t.Fatalf("a fast call announced itself: %q", notice.String())
	}
}

func TestASlowCallNamesTheCommandItIsWaitingOn(t *testing.T) {
	notice := &bytes.Buffer{}
	command := []string{"aos", "_launch-agent", "advocate"}
	value, err := whileWaiting2(notice, command, func() (string, error) {
		time.Sleep(slowCallNotice + 200*time.Millisecond)
		return "claude", nil
	})
	if err != nil || value != "claude" {
		t.Fatalf("the notice changed the answer: %q %v", value, err)
	}
	want := "aterm: waiting on `aos _launch-agent advocate`"
	if !strings.Contains(notice.String(), want) {
		t.Fatalf("notice = %q, want %q", notice.String(), want)
	}
}
