package main

import "embed"

// templatesFS holds the canonical, host-agnostic source of truth for every
// file `apply` renders. The repo template is never touched by Warp; rendered
// copies are derived and disposable. See project-a-coily-exec-warp.md.
//
//go:embed templates
var templatesFS embed.FS
