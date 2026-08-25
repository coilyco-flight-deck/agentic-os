package main

import (
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

func interactiveTTY(stdin, stdout *os.File) bool {
	for _, file := range []*os.File{stdin, stdout} {
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

// pickRoleAndSeat runs in the terminal the operator typed in, before any window
// is spawned, because the list has to appear where the keyboard already is.
func pickRoleAndSeat(document rosterDocument) (string, string, error) {
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
	))
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
	))
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
