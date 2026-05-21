package main

import "fmt"

// valueKind classifies how a setting's value translates between the TOML
// layer and the SQLite layer. See "Three layers of state" in
// project-a-coily-exec-warp.md.
type valueKind int

const (
	kindBool   valueKind = iota // TOML bool <-> JSON bool
	kindInt                     // TOML int  <-> JSON number
	kindEnum                    // string enum; SQLite spelling is per-key (see note)
	kindOpaque                  // value Warp owns or whose SQLite spelling is unverified: doctor-only
)

// settingMap pairs one TOML key path with its SQLite generic_string_objects
// storage_key, and carries both the canonical TOML value and the exact value
// the SQLite layer should hold.
//
// The names do not mechanically transform, and neither do the values: Warp's
// enum encoding is inconsistent across keys (view_mode stores lowercase
// "expanded", primary_info stores PascalCase "Command"). So kindEnum carries
// an explicit SQLiteValue rather than a computed transform. Keys whose SQLite
// spelling is not yet verified are kindOpaque - doctor reports their drift but
// apply never writes them.
type settingMap struct {
	TOMLPath    string // dotted path in settings.toml, for labelling
	StorageKey  string // SQLite generic_string_objects storage_key
	Kind        valueKind
	Canonical   any    // value templates/settings.toml.tmpl defines
	SQLiteValue string // exact value the SQLite layer should hold (kindEnum only)
}

// settingMaps is the embedded reconciliation table. Canonical mirrors
// templates/settings.toml.tmpl and must be kept in step with it.
//
// SQLiteValue spellings for kindEnum are observed from a live database, not
// from Warp source - reverify if Warp changes its settings serialization.
// input_mode and theme are kindOpaque: their SQLite spelling is unverified,
// so the tool reports their drift but does not auto-write them.
var settingMaps = []settingMap{
	{"privacy.crash_reporting_enabled", "CrashReportingEnabled", kindBool, true, ""},
	{"privacy.telemetry_enabled", "TelemetryEnabled", kindBool, true, ""},
	{"notifications.toast_duration_secs", "NotificationToastDurationSecs", kindInt, int64(8), ""},
	{"terminal.input.alias_expansion_enabled", "AliasExpansionEnabled", kindBool, true, ""},
	{"terminal.input.completions_open_while_typing", "CompletionsOpenWhileTyping", kindBool, true, ""},
	{"workflows.show_global_workflows_in_universal_search", "ShowGlobalWorkflowsInUniversalSearch", kindBool, true, ""},
	{"appearance.vertical_tabs.enabled", "UseVerticalTabs", kindBool, true, ""},
	{"agents.mcp_servers.file_based_mcp_enabled", "FileBasedMcpEnabled", kindBool, false, ""},
	{"agents.profiles.agent_mode_execute_readonly_commands", "AgentModeExecuteReadonlyCommands", kindBool, false, ""},
	{"agents.warp_agent.is_any_ai_enabled", "IsAnyAIEnabled", kindBool, false, ""},
	{"code.indexing.agent_mode_codebase_context_auto_indexing", "AgentModeCodebaseContextAutoIndexing", kindBool, false, ""},
	{"account.is_settings_sync_enabled", "IsSettingsSyncEnabled", kindBool, false, ""},
	{"general.default_session_mode", "DefaultSessionMode", kindEnum, "terminal", "Terminal"},
	{"appearance.tabs.workspace_decoration_visibility", "WorkspaceDecorationVisibility", kindEnum, "always_show", "AlwaysShow"},
	{"appearance.vertical_tabs.view_mode", "VerticalTabsViewMode", kindEnum, "expanded", "expanded"},
	{"appearance.vertical_tabs.primary_info", "VerticalTabsPrimaryInfo", kindEnum, "command", "Command"},
	{"appearance.input.input_mode", "InputMode", kindOpaque, "pinned_to_bottom", ""},
	{"appearance.themes.theme", "Theme", kindOpaque, nil, ""},
}

// expected returns the value the SQLite layer should hold for this setting.
// ok is false for kindOpaque (and for values that do not match their kind),
// which apply skips and doctor reports as a manual NOTE.
func (m settingMap) expected() (out any, ok bool) {
	switch m.Kind {
	case kindBool:
		b, isBool := m.Canonical.(bool)
		return b, isBool
	case kindInt:
		switch n := m.Canonical.(type) {
		case int64:
			return n, true
		case int:
			return int64(n), true
		}
		return nil, false
	case kindEnum:
		if m.SQLiteValue == "" {
			return nil, false
		}
		return m.SQLiteValue, true
	default: // kindOpaque
		return nil, false
	}
}

// valuesEqual compares two JSON-shaped values for reconciliation purposes.
// Numbers cross the JSON boundary as float64, so it normalizes through a
// canonical string form.
func valuesEqual(a, b any) bool {
	return fmt.Sprintf("%v", normalizeNum(a)) == fmt.Sprintf("%v", normalizeNum(b))
}

func normalizeNum(v any) any {
	switch n := v.(type) {
	case int64:
		return float64(n)
	case int:
		return float64(n)
	}
	return v
}
