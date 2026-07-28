package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"strconv"
	"testing"
	"time"
)

func TestDialSOCKS5UsesProxySideHostnameResolution(t *testing.T) {
	t.Parallel()
	target := listenTCP(t)
	proxy := listenTCP(t)
	targetErrors := make(chan error, 1)
	proxyErrors := make(chan error, 1)

	go func() {
		connection, err := target.Accept()
		if err != nil {
			targetErrors <- err
			return
		}
		defer connection.Close()
		_, err = io.Copy(connection, connection)
		targetErrors <- err
	}()

	_, targetPortRaw, err := net.SplitHostPort(target.Addr().String())
	if err != nil {
		t.Fatal(err)
	}
	targetPort, err := strconv.Atoi(targetPortRaw)
	if err != nil {
		t.Fatal(err)
	}
	go serveOneFakeSOCKS5(proxy, target.Addr().String(), "tailnet.example", targetPort, proxyErrors)

	connection, err := dialSOCKS5(
		proxy.Addr().String(),
		net.JoinHostPort("tailnet.example", targetPortRaw),
		2*time.Second,
	)
	if err != nil {
		t.Fatal(err)
	}
	defer connection.Close()
	message := []byte("tailnet-mcp")
	if _, err := connection.Write(message); err != nil {
		t.Fatal(err)
	}
	response := make([]byte, len(message))
	if _, err := io.ReadFull(connection, response); err != nil {
		t.Fatal(err)
	}
	if string(response) != string(message) {
		t.Fatalf("echo response = %q", response)
	}
	_ = connection.Close()
	_ = proxy.Close()
	_ = target.Close()
	if err := <-proxyErrors; err != nil {
		t.Fatal(err)
	}
	if err := <-targetErrors; err != nil {
		t.Fatal(err)
	}
}

func listenTCP(t *testing.T) net.Listener {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_ = listener.Close()
	})
	return listener
}

func serveOneFakeSOCKS5(
	listener net.Listener,
	upstream string,
	wantHost string,
	wantPort int,
	result chan<- error,
) {
	connection, err := listener.Accept()
	if err != nil {
		result <- err
		return
	}
	defer connection.Close()
	greeting := make([]byte, 3)
	if _, err := io.ReadFull(connection, greeting); err != nil {
		result <- err
		return
	}
	if string(greeting) != string([]byte{5, 1, 0}) {
		result <- fmt.Errorf("unexpected SOCKS5 greeting %v", greeting)
		return
	}
	if _, err := connection.Write([]byte{5, 0}); err != nil {
		result <- err
		return
	}
	header := make([]byte, 4)
	if _, err := io.ReadFull(connection, header); err != nil {
		result <- err
		return
	}
	if header[0] != 5 || header[1] != 1 || header[3] != 3 {
		result <- fmt.Errorf("unexpected SOCKS5 connect header %v", header)
		return
	}
	length := []byte{0}
	if _, err := io.ReadFull(connection, length); err != nil {
		result <- err
		return
	}
	host := make([]byte, int(length[0]))
	port := make([]byte, 2)
	if _, err := io.ReadFull(connection, host); err != nil {
		result <- err
		return
	}
	if _, err := io.ReadFull(connection, port); err != nil {
		result <- err
		return
	}
	if string(host) != wantHost || int(binary.BigEndian.Uint16(port)) != wantPort {
		result <- fmt.Errorf("SOCKS5 target = %s:%d", host, binary.BigEndian.Uint16(port))
		return
	}
	upstreamConnection, err := net.Dial("tcp", upstream)
	if err != nil {
		result <- err
		return
	}
	defer upstreamConnection.Close()
	if _, err := connection.Write([]byte{5, 0, 0, 1, 127, 0, 0, 1, 0, 0}); err != nil {
		result <- err
		return
	}
	done := make(chan struct{}, 2)
	go func() {
		_, _ = io.Copy(upstreamConnection, connection)
		done <- struct{}{}
	}()
	go func() {
		_, _ = io.Copy(connection, upstreamConnection)
		done <- struct{}{}
	}()
	<-done
	result <- nil
}
