package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
)

var (
	rosterSlugStyle    = lipgloss.NewStyle().Bold(true)
	rosterPurposeStyle = lipgloss.NewStyle().Faint(true)
)

// The controlling terminal, which `aterm > log` still has even though stdout
// is a file. Absent on Windows, where the open fails and the check degrades.
const controllingTerminal = "/dev/tty"

func interactiveTTY(stdin, stdout *os.File) bool {
	if characterDevices(stdin, stdout) {
		return true
	}
	file, err := os.OpenFile(controllingTerminal, os.O_RDWR, 0)
	if err != nil {
		return false
	}
	return file.Close() == nil
}

func characterDevices(files ...*os.File) bool {
	for _, file := range files {
		if file == nil {
			return false
		}
		info, err := file.Stat()
		if err != nil || info.Mode()&os.ModeCharDevice == 0 {
			return false
		}
	}
	return true
}

// openConsole points the form at the terminal rather than at stdout, so
// redirecting output does not silently disable the picker.
func openConsole() (io.Reader, io.Writer, func()) {
	if characterDevices(os.Stdin, os.Stdout) {
		return os.Stdin, os.Stdout, func() {}
	}
	file, err := os.OpenFile(controllingTerminal, os.O_RDWR, 0)
	if err != nil {
		return os.Stdin, os.Stdout, func() {}
	}
	return file, file, func() { _ = file.Close() }
}

// pickRoleAndSeat runs in the terminal the operator typed in, before any window
// is spawned, because the list has to appear where the keyboard already is.
func pickRoleAndSeat(document rosterDocument) (string, string, error) {
	input, output, closeConsole := openConsole()
	defer closeConsole()
	roleOptions := make([]huh.Option[string], 0, len(document.Items))
	for _, item := range document.Items {
		if len(item.nativeSeats()) == 0 {
			continue
		}
		roleOptions = append(roleOptions, huh.NewOption(item.label(), item.Slug))
	}
	if len(roleOptions) == 0 {
		return "", "", fmt.Errorf("no live role has a launchable native seat")
	}
	role := ""
	form := huh.NewForm(huh.NewGroup(
		huh.NewSelect[string]().
			Title("Role").
			Description("Which charter is this window?").
			Options(roleOptions...).
			Value(&role),
	)).WithInput(input).WithOutput(output)
	if err := form.Run(); err != nil {
		return "", "", pickerError(err)
	}
	selected, ok := document.role(role)
	if !ok {
		return "", "", fmt.Errorf("selected role %q left the roster mid-pick", role)
	}
	seats := selected.nativeSeats()
	if len(seats) == 1 {
		return role, seats[0].Harness, nil
	}
	seatOptions := make([]huh.Option[string], 0, len(seats))
	for _, item := range seats {
		seatOptions = append(seatOptions, huh.NewOption(seatLabel(item), item.Harness))
	}
	seat := ""
	seatForm := huh.NewForm(huh.NewGroup(
		huh.NewSelect[string]().
			Title("Seat").
			Description(selected.Purpose).
			Options(seatOptions...).
			Value(&seat),
	)).WithInput(input).WithOutput(output)
	if err := seatForm.Run(); err != nil {
		return "", "", pickerError(err)
	}
	return role, seat, nil
}

func pickerError(err error) error {
	if err == huh.ErrUserAborted {
		return fmt.Errorf("nothing launched")
	}
	return fmt.Errorf("pick a role: %w", err)
}

func seatLabel(seat rosterSeat) string {
	label := seat.Harness
	if name := strings.TrimSpace(seat.Name); name != "" {
		subject, _, _ := strings.Cut(strings.TrimSpace(seat.Pronouns), "/")
		if subject = strings.TrimSpace(subject); subject != "" {
			name += " [" + subject + "]"
		}
		label += " // " + name
	}
	if tier := strings.TrimSpace(seat.Tier); tier != "" {
		label += " // " + tier
	}
	return label
}

// writeRosterJSON is the machine twin of writeRoster, for a launcher, a
// dashboard, or anything scripting aterm.
func writeRosterJSON(writer io.Writer, document rosterDocument) error {
	encoded, err := json.MarshalIndent(listRoster(document), "", "  ")
	if err != nil {
		return fmt.Errorf("marshal the roster: %w", err)
	}
	_, err = fmt.Fprintf(writer, "%s\n", encoded)
	return err
}

// writeRoster is the non-interactive twin of the picker, for a pipe or a
// terminal that cannot host a form.
func writeRoster(writer io.Writer, document rosterDocument) error {
	for _, item := range document.Items {
		seats := item.nativeSeats()
		names := make([]string, 0, len(seats))
		for _, seat := range seats {
			names = append(names, seat.Harness)
		}
		if len(names) == 0 {
			names = append(names, "(no native seat)")
		}
		if _, err := fmt.Fprintf(
			writer,
			"%s // %s // %s\n  %s\n",
			rosterSlugStyle.Render(item.Slug),
			item.DisplayName,
			strings.Join(names, ", "),
			rosterPurposeStyle.Render(item.Purpose),
		); err != nil {
			return err
		}
	}
	return nil
}
