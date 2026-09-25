package main

import (
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// terminateGrace is how long an ended session gets between SIGTERM and SIGKILL.
const terminateGrace = 3 * time.Second

type processEntry struct {
	PID     int
	PPID    int
	Command string
}

// listProcesses reads this user's processes, which is all a session may end.
func listProcesses() ([]processEntry, error) {
	command := exec.Command("ps", "-xo", "pid=,ppid=,command=")
	command.Env = append(os.Environ(), "LC_ALL=C")
	raw, err := command.Output()
	if err != nil {
		return nil, err
	}
	var entries []processEntry
	for _, line := range strings.Split(string(raw), "\n") {
		pidText, rest, _ := strings.Cut(strings.TrimSpace(line), " ")
		ppidText, commandText, _ := strings.Cut(strings.TrimSpace(rest), " ")
		pid, pidErr := strconv.Atoi(pidText)
		ppid, ppidErr := strconv.Atoi(ppidText)
		if pidErr != nil || ppidErr != nil {
			continue
		}
		entries = append(entries, processEntry{PID: pid, PPID: ppid, Command: strings.TrimSpace(commandText)})
	}
	return entries, nil
}
