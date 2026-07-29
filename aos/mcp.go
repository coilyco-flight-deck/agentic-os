package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net"
	"net/netip"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	containerMCPInventory = "/run/aos/mcp/mcporter.json"
	tailnetDockerNetwork  = "ward-tailnet"
	tailnetSOCKS5Proxy    = "tailscale-proxy:1055"
	tailnetSOCKS5URL      = "socks5h://" + tailnetSOCKS5Proxy
	tailnetListenPortBase = 39000
)

var (
	tailscaleIPv4 = netip.MustParsePrefix("100.64.0.0/10")
	tailscaleIPv6 = netip.MustParsePrefix("fd7a:115c:a1e0::/48")
)

type mcpLaunchConfig struct {
	Inventory      string
	TailnetNetwork string
	Forwards       []tailnetForward
}

type mcpEndpoint struct {
	Server         string
	URL            *url.URL
	TailnetAddress netip.Addr
}

type tailnetForward struct {
	Server     string `json:"server"`
	TargetHost string `json:"target_host"`
	TargetPort int    `json:"target_port"`
	ListenPort int    `json:"listen_port"`
}

func (f tailnetForward) listenAddress() string {
	return net.JoinHostPort("127.0.0.1", strconv.Itoa(f.ListenPort))
}

func (f tailnetForward) targetAddress() string {
	return net.JoinHostPort(f.TargetHost, strconv.Itoa(f.TargetPort))
}

func (f tailnetForward) encode() (string, error) {
	data, err := json.Marshal(f)
	if err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(data), nil
}

func decodeTailnetForward(value string) (tailnetForward, error) {
	data, err := base64.RawURLEncoding.DecodeString(value)
	if err != nil {
		return tailnetForward{}, fmt.Errorf("decode tailnet forward: %w", err)
	}
	var forward tailnetForward
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&forward); err != nil {
		return tailnetForward{}, fmt.Errorf("decode tailnet forward: %w", err)
	}
	if err := validateTailnetForward(forward); err != nil {
		return tailnetForward{}, err
	}
	return forward, nil
}

func decodeTailnetForwards(values []string) ([]tailnetForward, error) {
	forwards := make([]tailnetForward, 0, len(values))
	for _, value := range values {
		forward, err := decodeTailnetForward(value)
		if err != nil {
			return nil, err
		}
		forwards = append(forwards, forward)
	}
	return forwards, nil
}

func validateTailnetForward(forward tailnetForward) error {
	if strings.TrimSpace(forward.Server) == "" {
		return fmt.Errorf("tailnet forward server must not be empty")
	}
	if strings.TrimSpace(forward.TargetHost) == "" {
		return fmt.Errorf("tailnet forward target host must not be empty")
	}
	if forward.TargetPort < 1 || forward.TargetPort > 65535 {
		return fmt.Errorf("tailnet forward target port %d is invalid", forward.TargetPort)
	}
	if forward.ListenPort < 1024 || forward.ListenPort > 65535 {
		return fmt.Errorf("tailnet forward listen port %d is outside 1024..65535", forward.ListenPort)
	}
	return nil
}

func discoverMCPLaunch(ctx context.Context) (mcpLaunchConfig, error) {
	config := mcpLaunchConfig{}
	if dockerNetworkExists(ctx, tailnetDockerNetwork) {
		config.TailnetNetwork = tailnetDockerNetwork
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return config, nil
	}
	inventory := filepath.Join(home, ".mcporter", "mcporter.json")
	info, err := os.Stat(inventory)
	if err != nil {
		if os.IsNotExist(err) {
			return config, nil
		}
		return mcpLaunchConfig{}, fmt.Errorf("inspect host MCP inventory: %w", err)
	}
	if !info.Mode().IsRegular() {
		return mcpLaunchConfig{}, fmt.Errorf("host MCP inventory is not a regular file")
	}
	endpoints, err := loadMCPEndpoints(inventory)
	if err != nil {
		return mcpLaunchConfig{}, err
	}
	config.Inventory = inventory
	tailnetEndpoints := resolveTailnetEndpoints(ctx, endpoints)
	if len(tailnetEndpoints) == 0 || config.TailnetNetwork == "" {
		return config, nil
	}
	if tailnetListenPortBase+len(tailnetEndpoints) > 65535 {
		return mcpLaunchConfig{}, fmt.Errorf("host MCP inventory has too many tailnet endpoints")
	}
	for index, endpoint := range tailnetEndpoints {
		port, err := endpointPort(endpoint.URL)
		if err != nil {
			return mcpLaunchConfig{}, fmt.Errorf("MCP server %s: %w", endpoint.Server, err)
		}
		if endpoint.URL.Scheme != "http" {
			return mcpLaunchConfig{}, fmt.Errorf(
				"MCP server %s uses %s over the tailnet; standalone bridging currently requires http",
				endpoint.Server,
				endpoint.URL.Scheme,
			)
		}
		config.Forwards = append(config.Forwards, tailnetForward{
			Server:     endpoint.Server,
			TargetHost: endpoint.TailnetAddress.String(),
			TargetPort: port,
			ListenPort: tailnetListenPortBase + index,
		})
	}
	return config, nil
}

func loadMCPEndpoints(path string) ([]mcpEndpoint, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read host MCP inventory: %w", err)
	}
	var document struct {
		MCPServers map[string]json.RawMessage `json:"mcpServers"`
	}
	if err := json.Unmarshal(data, &document); err != nil {
		return nil, fmt.Errorf("parse host MCP inventory: %w", err)
	}
	var endpoints []mcpEndpoint
	for name, raw := range document.MCPServers {
		var server struct {
			BaseURL string `json:"baseUrl"`
			URL     string `json:"url"`
		}
		if err := json.Unmarshal(raw, &server); err != nil {
			return nil, fmt.Errorf("parse MCP server %s: %w", name, err)
		}
		rawURL := strings.TrimSpace(server.BaseURL)
		if rawURL == "" {
			rawURL = strings.TrimSpace(server.URL)
		}
		if rawURL == "" {
			continue
		}
		parsed, err := url.Parse(rawURL)
		if err != nil || parsed.Hostname() == "" {
			return nil, fmt.Errorf("MCP server %s has an invalid URL", name)
		}
		switch parsed.Scheme {
		case "http", "https":
		default:
			continue
		}
		endpoints = append(endpoints, mcpEndpoint{Server: name, URL: parsed})
	}
	sort.Slice(endpoints, func(i, j int) bool {
		return endpoints[i].Server < endpoints[j].Server
	})
	return endpoints, nil
}

func resolveTailnetEndpoints(ctx context.Context, endpoints []mcpEndpoint) []mcpEndpoint {
	lookupCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	cache := map[string]netip.Addr{}
	var tailnet []mcpEndpoint
	for _, endpoint := range endpoints {
		host := endpoint.URL.Hostname()
		address, ok := cache[host]
		if !ok {
			address, _ = resolveTailnetAddress(lookupCtx, host)
			cache[host] = address
		}
		if address.IsValid() {
			endpoint.TailnetAddress = address
			tailnet = append(tailnet, endpoint)
		}
	}
	return tailnet
}

func resolveTailnetAddress(ctx context.Context, host string) (netip.Addr, bool) {
	if address, err := netip.ParseAddr(host); err == nil {
		return address, isTailnetAddress(address)
	}
	addresses, err := net.DefaultResolver.LookupNetIP(ctx, "ip", host)
	if err != nil {
		return netip.Addr{}, false
	}
	for _, address := range addresses {
		address = address.Unmap()
		if isTailnetAddress(address) {
			return address, true
		}
	}
	return netip.Addr{}, false
}

func isTailnetAddress(address netip.Addr) bool {
	return tailscaleIPv4.Contains(address) || tailscaleIPv6.Contains(address)
}

func endpointPort(endpoint *url.URL) (int, error) {
	if rawPort := endpoint.Port(); rawPort != "" {
		port, err := strconv.Atoi(rawPort)
		if err != nil || port < 1 || port > 65535 {
			return 0, fmt.Errorf("URL port %q is invalid", rawPort)
		}
		return port, nil
	}
	switch endpoint.Scheme {
	case "http":
		return 80, nil
	case "https":
		return 443, nil
	default:
		return 0, fmt.Errorf("URL scheme %q has no default port", endpoint.Scheme)
	}
}

func dockerNetworkExists(ctx context.Context, name string) bool {
	inspectCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	command := exec.CommandContext(inspectCtx, "docker", "network", "inspect", name)
	command.Stdout = nil
	command.Stderr = nil
	return command.Run() == nil
}

func stageMCPProjection(
	ctx context.Context,
	opts bootstrapOptions,
	runner commandRunner,
) error {
	if strings.TrimSpace(opts.MCPInventory) == "" {
		return nil
	}
	inventory := opts.MCPInventory
	if len(opts.TailnetForwards) > 0 {
		projected := filepath.Join(opts.AgentHome, ".aos", "mcporter.json")
		if err := projectTailnetMCPInventory(inventory, projected, opts.TailnetForwards); err != nil {
			return err
		}
		inventory = projected
	}
	if err := runner.Run(
		ctx,
		opts.AgentComposeBin,
		"mcp",
		"--inventory",
		inventory,
		"--home",
		opts.AgentHome,
	); err != nil {
		return fmt.Errorf("project MCP inventory: %w", err)
	}
	return nil
}

func projectTailnetMCPInventory(
	source string,
	target string,
	forwards []tailnetForward,
) error {
	data, err := os.ReadFile(source)
	if err != nil {
		return fmt.Errorf("read staged MCP inventory: %w", err)
	}
	var document map[string]json.RawMessage
	if err := json.Unmarshal(data, &document); err != nil {
		return fmt.Errorf("parse staged MCP inventory: %w", err)
	}
	var servers map[string]json.RawMessage
	if err := json.Unmarshal(document["mcpServers"], &servers); err != nil {
		return fmt.Errorf("parse staged MCP servers: %w", err)
	}
	for _, forward := range forwards {
		if err := validateTailnetForward(forward); err != nil {
			return err
		}
		raw, ok := servers[forward.Server]
		if !ok {
			return fmt.Errorf("tailnet MCP server %s is absent from the staged inventory", forward.Server)
		}
		var server map[string]json.RawMessage
		if err := json.Unmarshal(raw, &server); err != nil {
			return fmt.Errorf("parse tailnet MCP server %s: %w", forward.Server, err)
		}
		key := "baseUrl"
		rawURL, ok := server[key]
		if !ok {
			key = "url"
			rawURL, ok = server[key]
		}
		if !ok {
			return fmt.Errorf("tailnet MCP server %s has no URL", forward.Server)
		}
		var value string
		if err := json.Unmarshal(rawURL, &value); err != nil {
			return fmt.Errorf("parse tailnet MCP server %s URL: %w", forward.Server, err)
		}
		parsed, err := url.Parse(value)
		if err != nil || parsed.Scheme != "http" {
			return fmt.Errorf("tailnet MCP server %s needs an http URL", forward.Server)
		}
		parsed.Host = net.JoinHostPort("127.0.0.1", strconv.Itoa(forward.ListenPort))
		server[key], err = json.Marshal(parsed.String())
		if err != nil {
			return fmt.Errorf("encode tailnet MCP server %s URL: %w", forward.Server, err)
		}
		servers[forward.Server], err = json.Marshal(server)
		if err != nil {
			return fmt.Errorf("encode tailnet MCP server %s: %w", forward.Server, err)
		}
	}
	document["mcpServers"], err = json.Marshal(servers)
	if err != nil {
		return fmt.Errorf("encode staged MCP servers: %w", err)
	}
	output, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		return fmt.Errorf("encode staged MCP inventory: %w", err)
	}
	output = append(output, '\n')
	if err := os.MkdirAll(filepath.Dir(target), 0o700); err != nil {
		return fmt.Errorf("create staged MCP directory: %w", err)
	}
	if err := os.WriteFile(target, output, 0o600); err != nil {
		return fmt.Errorf("write staged MCP inventory: %w", err)
	}
	return nil
}
