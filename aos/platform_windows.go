//go:build windows

package main

import "fmt"

func hostIdentity() (int, int) {
	return 1000, 1000
}

func execAs(_, _ int, _ execSpec) error {
	return fmt.Errorf("container process replacement is supported only by the Linux image")
}
