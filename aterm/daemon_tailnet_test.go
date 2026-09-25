package main

import (
	"context"
	"errors"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/coder/websocket"
)

func peerWith(login string, tags ...string) tailnetPeer {
	var peer tailnetPeer
	peer.UserProfile.LoginName = login
	peer.Node.Tags = tags
	return peer
}

func TestAdmitPeerTakesTheOwnerAndAllowedTagsOnly(t *testing.T) {
	allow := []string{"tag:physical"}
	for _, testCase := range []struct {
		name  string
		peer  tailnetPeer
		admit bool
	}{
		{"the owner's own phone", peerWith("kai@example.com"), true},
		{"another tailnet user", peerWith("guest@example.com"), false},
		{"an untagged device with no login", peerWith(""), false},
		{"a physical tower", peerWith("tagged-devices", "tag:kai-tower-3026", "tag:physical"), true},
		{"a CI runner", peerWith("tagged-devices", "tag:ci"), false},
		{"a tagged device claiming the owner's login", peerWith("kai@example.com", "tag:proxy"), false},
	} {
		err := admitPeer(testCase.peer, "kai@example.com", allow)
		if (err == nil) != testCase.admit {
			t.Fatalf("%s: admitted=%v, want %v (%v)", testCase.name, err == nil, testCase.admit, err)
		}
	}
}

const testFQDN = "mac.example.ts.net"

// tailnetServer serves the tailnet policy over TLS on loopback, and a client
// that reaches it by the tailnet name, as a browser on another device would.
func tailnetServer(t *testing.T, whois func(string) (tailnetPeer, error)) (string, *http.Client, *daemon) {
	t.Helper()
	d := newDaemon(func(string, ...any) {})
	d.clientDir = t.TempDir()
	if err := os.WriteFile(filepath.Join(d.clientDir, "index.html"), []byte("aterm client"), 0o644); err != nil {
		t.Fatal(err)
	}
	node := tailnetNode{FQDN: testFQDN, IPv4: "127.0.0.1", Owner: "kai@example.com"}
	server := httptest.NewTLSServer(d.handler(tailnetPolicy(node, []string{"tag:physical"}, []string{"https://coilyco.dev"}, whois)))
	t.Cleanup(server.Close)
	_, port, _ := net.SplitHostPort(server.Listener.Addr().String())
	// Trust the test server's own certificate. It names example.com, and the
	// dialer below routes the tailnet name to it.
	trusted := server.Client().Transport.(*http.Transport).TLSClientConfig.Clone()
	trusted.ServerName = "example.com"
	client := &http.Client{Transport: &http.Transport{
		TLSClientConfig: trusted,
		DialContext: func(ctx context.Context, network, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, network, server.Listener.Addr().String())
		},
	}}
	return "https://" + testFQDN + ":" + port, client, d
}

func TestTailnetServesTheClientToAnAdmittedDeviceOnly(t *testing.T) {
	var calls atomic.Int32
	admitted := true
	base, client, _ := tailnetServer(t, func(string) (tailnetPeer, error) {
		calls.Add(1)
		if admitted {
			return peerWith("tagged-devices", "tag:physical"), nil
		}
		return peerWith("guest@example.com"), nil
	})
	response, err := client.Get(base + "/")
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	body, _ := io.ReadAll(response.Body)
	response.Body.Close()
	if response.StatusCode != http.StatusOK || string(body) != "aterm client" {
		t.Fatalf("an admitted device should get the client: %d %q", response.StatusCode, body)
	}
	if response, err = client.Get(base + "/index.html"); err != nil || response.StatusCode != http.StatusOK {
		t.Fatalf("second load: %v %v", err, response)
	}
	response.Body.Close()
	if calls.Load() != 1 {
		t.Fatalf("a page load should cost one whois, got %d", calls.Load())
	}
}

func TestTailnetRefusesAnotherUserAndAnUnnamedHost(t *testing.T) {
	base, client, _ := tailnetServer(t, func(string) (tailnetPeer, error) { return peerWith("guest@example.com"), nil })
	if response, err := client.Get(base + "/"); err != nil || response.StatusCode != http.StatusForbidden {
		t.Fatalf("another tailnet user must get 403: %v %v", err, response)
	}
	// Reached by address rather than by name is not how the client is served.
	request, _ := http.NewRequest(http.MethodGet, base+"/", nil)
	request.Host = "127.0.0.1"
	if response, err := client.Do(request); err != nil || response.StatusCode != http.StatusForbidden {
		t.Fatalf("a request not addressed to the tailnet name must get 403: %v %v", err, response)
	}
	broken, brokenClient, _ := tailnetServer(t, func(string) (tailnetPeer, error) { return tailnetPeer{}, errors.New("tailscaled down") })
	if response, err := brokenClient.Get(broken + "/"); err != nil || response.StatusCode != http.StatusForbidden {
		t.Fatalf("an unanswered whois must refuse, not admit: %v %v", err, response)
	}
}

func TestTailnetWebsocketTakesOnlyThePageItServed(t *testing.T) {
	base, client, _ := tailnetServer(t, func(string) (tailnetPeer, error) { return peerWith("kai@example.com"), nil })
	address := "wss" + strings.TrimPrefix(base, "https") + "/"
	dial := func(origin string) (*websocket.Conn, *http.Response, error) {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return websocket.Dial(ctx, address, &websocket.DialOptions{HTTPClient: client, HTTPHeader: http.Header{"Origin": {origin}}})
	}
	for _, origin := range []string{base, "https://coilyco.dev", "https://COILYCO.dev"} {
		ws, _, err := dial(origin)
		if err != nil {
			t.Fatalf("origin %q must open a socket: %v", origin, err)
		}
		_ = ws.CloseNow()
	}
	for _, origin := range []string{"https://evil.example", "http://" + strings.TrimPrefix(base, "https://"), "http://localhost:5173", "http://coilyco.dev", "https://coilyco.dev.evil.example", "https://www.coilyco.dev"} {
		if ws, response, err := dial(origin); err == nil {
			_ = ws.CloseNow()
			t.Fatalf("origin %q must be refused", origin)
		} else if response == nil || response.StatusCode != http.StatusForbidden {
			t.Fatalf("origin %q should get 403, got %v", origin, response)
		}
	}
}

func TestLoopbackServesTheClientWhenOneIsInstalled(t *testing.T) {
	d := newDaemon(func(string, ...any) {})
	server := httptest.NewServer(d.handler(loopbackPolicy()))
	t.Cleanup(server.Close)
	if response, err := http.Get(server.URL + "/"); err != nil || response.StatusCode != http.StatusNotFound {
		t.Fatalf("no client installed should be 404: %v %v", err, response)
	}
	d.clientDir = t.TempDir()
	if err := os.WriteFile(filepath.Join(d.clientDir, "index.html"), []byte("aterm client"), 0o644); err != nil {
		t.Fatal(err)
	}
	response, err := http.Get(server.URL + "/")
	if err != nil || response.StatusCode != http.StatusOK {
		t.Fatalf("an installed client should be served: %v %v", err, response)
	}
	response.Body.Close()
}
