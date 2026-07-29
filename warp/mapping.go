package main

import "fmt"

// valueKind classifies a setting's TOML <-> SQLite crossing.
type valueKind int

const (
	kindBool valueKind = iota
	kindInt
	kindEnum
	kindOpaque
)

// settingMap pairs a TOML key path with its SQLite storage_key.
type settingMap struct {
	TOMLPath    string
	StorageKey  string
	Kind        valueKind
	Canonical   any
	SQLiteValue string
}

// Reconciliation table. Mirror with templates/settings.toml.tmpl.
var settingMaps = []settingMap{
	{"privacy.crash_reporting_enabled", "CrashReportingEnabled", kindBool, true, ""},
	{"privacy.telemetry_enabled", "TelemetryEnabled", kindBool, true, ""},
	{"notifications.toast_duration_secs", "NotificationToastDurationSecs", kindInt, int64(8), ""},
	{"terminal.input.alias_expansion_enabled", "AliasExpansionEnabled", kindBool, true, ""},
	{"terminal.input.completions_open_while_typing", "CompletionsOpenWhileTyping", kindBool, true, ""},
	{"workflows.show_global_workflows_in_universal_search", "ShowGlobalWorkflowsInUniversalSearch", kindBool, true, ""},
	{"appearance.vertical_tabs.enabled", "UseVerticalTabs", kindBool, false, ""},
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

// expected returns the SQLite value; ok=false for kindOpaque or type mismatch.
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
	default:
		return nil, false
	}
}

// valuesEqual normalizes numbers through float64 before string-compare.
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
