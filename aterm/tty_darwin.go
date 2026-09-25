package main

import "golang.org/x/sys/unix"

// flushInput discards what the terminal holds unread, such as a reply to a
// query the card made. TIOCSETAF re-applies the settings and flushes input.
func flushInput(fd uintptr) error {
	settings, err := unix.IoctlGetTermios(int(fd), unix.TIOCGETA)
	if err != nil {
		return err
	}
	return unix.IoctlSetTermios(int(fd), unix.TIOCSETAF, settings)
}
