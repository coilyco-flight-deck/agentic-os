package main

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

const sessionCommand = "_session"

var (
	sessionNoticeStyle  = lipgloss.NewStyle().Faint(true)
	sessionFailureStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("1"))
)

// runSession is the inner half of the launch. Holding the window on a non-zero
// exit is why this exists rather than `-e`. See docs/aterm.md.
func runSession(argv []string, hold bool, stdin io.Reader, stdout, stderr io.Writer) int {
	if len(argv) == 0 {
		fmt.Fprintln(stderr, "aterm: "+sessionCommand+" needs a command after `--`")
		return 2
	}
	command := exec.Command(argv[0], argv[1:]...)
	command.Stdin = os.Stdin
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr
	err := command.Run()
	if err == nil {
		if hold {
			holdWindow(stdin, stdout, sessionNoticeStyle.Render("Session ended. Press Enter to close."))
		}
		return 0
	}
	code := 1
	var exitErr *exec.ExitError
	switch {
	case errors.As(err, &exitErr):
		code = exitErr.ExitCode()
		if code < 0 {
			code = 1
		}
	default:
		fmt.Fprintf(stderr, "\naterm: start %s: %v\n", argv[0], err)
	}
	holdWindow(stdin, stdout, sessionFailureStyle.Render(
		fmt.Sprintf("Session failed (exit %d). Press Enter to close.", code),
	))
	return code
}

// holdWindow keeps the pane readable after the child is gone. A non-interactive
// stdin will never answer, so it prints and returns instead.
func holdWindow(stdin io.Reader, stdout io.Writer, notice string) {
	fmt.Fprintf(stdout, "\n%s\n", notice)
	file, ok := stdin.(*os.File)
	if !ok {
		return
	}
	info, err := file.Stat()
	if err != nil || info.Mode()&os.ModeCharDevice == 0 {
		return
	}
	reader := bufio.NewReader(file)
	_, _ = reader.ReadString('\n')
}

// parseSessionArgs hand-parses because everything after the first `--` belongs
// to the child verbatim, including the child's own `--`.
func parseSessionArgs(argv []string) (bool, []string, error) {
	hold := false
	for index, value := range argv {
		switch value {
		case "--hold":
			hold = true
		case "--":
			return hold, argv[index+1:], nil
		default:
			return false, nil, fmt.Errorf(
				"%s has unsupported option %q",
				sessionCommand,
				strings.TrimSpace(value),
			)
		}
	}
	return false, nil, fmt.Errorf("%s needs a command after `--`", sessionCommand)
}
