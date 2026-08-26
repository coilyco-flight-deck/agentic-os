package main

import (
	"context"
	"fmt"
	"strings"
)

const launchFormat = "aterm.launch.v1"

type launchRequest struct {
	Role             string
	Seat             string
	Expression       string
	TaskTitle        string
	WorkingDirectory string
	AgentComposeBin  string
	AOSBin           string
	AlacrittyBin     string
	Extra            []string
	Hold             bool
}

type launchIdentity struct {
	Person          string `json:"person"`
	Role            string `json:"role"`
	RoleDisplayName string `json:"role_display_name"`
	Seat            string `json:"seat"`
	Name            string `json:"name"`
	Pronouns        string `json:"pronouns"`
	Annotation      string `json:"annotation"`
	Expression      string `json:"expression"`
	FavoriteColor   string `json:"favorite_color"`
}

type launchPlan struct {
	Format           string         `json:"format"`
	Identity         launchIdentity `json:"identity"`
	Brand            launchBrand    `json:"brand"`
	WorkingDirectory string         `json:"working_directory"`
	Shadowed         bool           `json:"shadowed"`
	Child            []string       `json:"child"`
	Executable       string         `json:"executable"`
	Arguments        []string       `json:"arguments"`
}

// composeChild mirrors the acompose shell function so the window runs the same
// runtime the bare command does. See agentic-os/shell/common.sh.
func composeChild(request launchRequest, agentCompose, aos string, shadowed bool) []string {
	launch := []string{agentCompose, "launch", request.Role, request.Seat}
	launch = append(launch, request.Extra...)
	if !shadowed {
		return launch
	}
	child := []string{
		aos, "_native-shadow",
		"--harness", request.Seat,
		"--role", request.Role,
		"--assigned-role", "--",
	}
	return append(child, launch...)
}

// nativeShadowAvailable probes the same way the acompose shell function does. An
// AOS without the shadow verb still launches, just without a leased workspace.
func nativeShadowAvailable(ctx context.Context, deps commandDeps, aos string) bool {
	command := []string{aos, "_native-shadow", "--probe"}
	return whileWaiting(deps.notice, command, func() error {
		return deps.run(ctx, command[0], command[1:]...)
	}) == nil
}

func buildLaunchPlan(
	document overlayDocument,
	request launchRequest,
	cwd string,
	self string,
	agentCompose string,
	aos string,
	shadowed bool,
) (launchPlan, error) {
	brand, err := buildBrand(document, request.TaskTitle)
	if err != nil {
		return launchPlan{}, err
	}
	child := composeChild(request, agentCompose, aos, shadowed)
	session := []string{self, sessionCommand}
	if request.Hold {
		session = append(session, "--hold")
	}
	session = append(session, "--")
	session = append(session, child...)
	arguments := []string{
		"--title", brand.Title,
		"--working-directory", cwd,
		"-o", "window.dynamic_title=false",
		"-o", "window.opacity=1.0",
		"-o", fmt.Sprintf(`colors.primary.background="%s"`, brand.Background),
		"-o", fmt.Sprintf(`colors.cursor.cursor="%s"`, brand.Accent),
		"-o", fmt.Sprintf(`colors.selection.background="%s"`, brand.Accent),
		"-o", fmt.Sprintf(`colors.selection.text="%s"`, brand.SelectionText),
		"-e",
	}
	arguments = append(arguments, session...)
	return launchPlan{
		Format: launchFormat,
		Identity: launchIdentity{
			Person:          document.Person,
			Role:            document.Role,
			RoleDisplayName: document.RoleDisplayName,
			Seat:            document.Seat.Harness,
			Name:            document.Seat.Name,
			Pronouns:        document.Seat.Pronouns,
			Annotation:      seatAnnotation(document),
			Expression:      document.Expression,
			FavoriteColor:   brand.Accent,
		},
		Brand:            brand,
		WorkingDirectory: cwd,
		Shadowed:         shadowed,
		Child:            child,
		Executable:       strings.TrimSpace(request.AlacrittyBin),
		Arguments:        arguments,
	}, nil
}
