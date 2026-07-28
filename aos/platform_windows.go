//go:build windows

package main

import "fmt"

func hostIdentity() (int, int) {
	return 1000, 1000
}

func chownPath(_ string, _ bool, _, _ int) error {
	return nil
}

func execAs(_, _ int, _ execSpec) error {
	return fmt.Errorf("container process replacement is supported only by the Linux image")
}

func startSOCKSForwarders(_, _ int, spec execSpec) error {
	if len(spec.TailnetForwards) == 0 {
		return nil
	}
	return fmt.Errorf("tailnet MCP forwarding is supported only by the Linux image")
}
