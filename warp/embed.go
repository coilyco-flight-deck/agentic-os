package main

import "embed"

// templatesFS is the source of truth for every file `apply` renders.

//go:embed templates
var templatesFS embed.FS
