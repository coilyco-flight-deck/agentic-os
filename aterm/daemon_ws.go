package main

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/url"

	"github.com/coder/websocket"
)

const (
	daemonWSEnv = "ATERM_DAEMON_WS"
	// Loopback only until the tailnet milestone brings client auth.
	// See docs/aterm-daemon.md.
	defaultDaemonWS = "127.0.0.1:7419"
)

// loopbackOrigins match an Origin's host and port. A browser sends Origin on
// every websocket, and nothing else here stops another site's page.
var loopbackOrigins = []string{"localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*", `\[::1\]`, `\[::1\]:*`}

// requireLoopback refuses a listen address that is not a loopback IP, since
// the listener has no auth beyond Origin.
func requireLoopback(address string) error {
	host, _, err := net.SplitHostPort(address)
	if err != nil {
		return fmt.Errorf("websocket address %q: %w", address, err)
	}
	if ip := net.ParseIP(host); ip == nil || !ip.IsLoopback() {
		return fmt.Errorf("websocket address %q is not a loopback IP, and tailnet auth is not built", address)
	}
	return nil
}

func isLoopbackHost(hostport string) bool {
	host := hostport
	if split, _, err := net.SplitHostPort(hostport); err == nil {
		host = split
	}
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

// websocketHandler carries the unix socket's frames, one per text message, to
// loopback browsers only. See docs/aterm-daemon.md.
func (d *daemon) websocketHandler() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		parsed, err := url.Parse(origin)
		if !isLoopbackHost(r.Host) || origin == "" || err != nil || !isLoopbackHost(parsed.Host) {
			http.Error(w, "aterm daemon: loopback browser origins only", http.StatusForbidden)
			return
		}
		ws, err := websocket.Accept(w, r, &websocket.AcceptOptions{OriginPatterns: loopbackOrigins})
		if err != nil {
			return
		}
		ws.SetReadLimit(maxFrame)
		d.serveConn(newWebsocketConn(r.Context(), ws), 0, true)
	})
}

func newWebsocketConn(ctx context.Context, ws *websocket.Conn) *conn {
	return &conn{
		readLine: func() ([]byte, error) {
			kind, data, err := ws.Read(ctx)
			if err == nil && kind != websocket.MessageText {
				return nil, errors.New("frames are text messages")
			}
			return data, err
		},
		writeLine: func(line []byte) error {
			writeCtx, cancel := context.WithTimeout(ctx, clientWriteTimeout)
			defer cancel()
			return ws.Write(writeCtx, websocket.MessageText, line)
		},
		closer: func() error { return ws.Close(websocket.StatusNormalClosure, "") },
	}
}

// listenWebsocket serves until the returned server is closed. A port already
// taken costs the browser clients, never the daemon.
func (d *daemon) listenWebsocket(address string) (*http.Server, error) {
	if err := requireLoopback(address); err != nil {
		return nil, err
	}
	listener, err := net.Listen("tcp", address)
	if err != nil {
		return nil, err
	}
	server := &http.Server{Handler: d.websocketHandler()}
	go func() { _ = server.Serve(listener) }()
	d.logf("serving websocket on ws://%s", listener.Addr())
	return server, nil
}
