package main

import "golang.org/x/sys/unix"

// flushInput discards what the terminal holds unread, such as a reply to a
// query the card made. See docs/aterm-daemon.md.
func flushInput(fd uintptr) error {
	return unix.IoctlSetInt(int(fd), unix.TCFLSH, unix.TCIFLUSH)
}
