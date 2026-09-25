package main

import "strings"

// sessionName names a session for who answers, not the harness: the role slug,
// the identity's slugified name, then the instance code. See docs/aterm-daemon.md.
func sessionName(name, role, instance string) string {
	if role == "" {
		return ""
	}
	if instance == "" {
		return role + "-" + slugify(name)
	}
	return role + "-" + slugify(name) + "-" + instance
}

// slugify lowercases a value and collapses any run of non-alphanumeric
// characters to a single hyphen, trimming a leading or trailing one.
func slugify(value string) string {
	var builder strings.Builder
	dashed := true // suppresses a leading hyphen
	for _, r := range strings.ToLower(value) {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			builder.WriteRune(r)
			dashed = false
			continue
		}
		if !dashed {
			builder.WriteByte('-')
			dashed = true
		}
	}
	return strings.TrimRight(builder.String(), "-")
}

func hasNameFlag(arguments []string) bool {
	for _, argument := range arguments {
		if argument == "--name" || argument == "-n" || strings.HasPrefix(argument, "--name=") {
			return true
		}
	}
	return false
}
