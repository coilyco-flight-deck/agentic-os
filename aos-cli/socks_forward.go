package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"os"
	"strconv"
	"sync"
	"time"
)

func runContainerSOCKSForward(fd int, proxy, target string) error {
	if os.Getenv("AOS_CONTAINER") != "1" {
		return fmt.Errorf("_container-socks-forward is internal to an AOS container")
	}
	if fd < 3 {
		return fmt.Errorf("_container-socks-forward needs an inherited listener fd")
	}
	file := os.NewFile(uintptr(fd), "aos-tailnet-listener")
	if file == nil {
		return fmt.Errorf("open inherited tailnet listener")
	}
	defer file.Close()
	listener, err := net.FileListener(file)
	if err != nil {
		return fmt.Errorf("open inherited tailnet listener: %w", err)
	}
	defer listener.Close()
	return serveSOCKSForward(listener, proxy, target)
}

func serveSOCKSForward(listener net.Listener, proxy, target string) error {
	for {
		client, err := listener.Accept()
		if err != nil {
			return err
		}
		go handleSOCKSForward(client, proxy, target)
	}
}

func handleSOCKSForward(client net.Conn, proxy, target string) {
	defer client.Close()
	upstream, err := dialSOCKS5(proxy, target, 10*time.Second)
	if err != nil {
		return
	}
	defer upstream.Close()

	var copies sync.WaitGroup
	copies.Add(2)
	go func() {
		defer copies.Done()
		_, _ = io.Copy(upstream, client)
		if tcp, ok := upstream.(*net.TCPConn); ok {
			_ = tcp.CloseWrite()
		}
	}()
	go func() {
		defer copies.Done()
		_, _ = io.Copy(client, upstream)
		if tcp, ok := client.(*net.TCPConn); ok {
			_ = tcp.CloseWrite()
		}
	}()
	copies.Wait()
}

func dialSOCKS5(proxy, target string, timeout time.Duration) (net.Conn, error) {
	connection, err := net.DialTimeout("tcp", proxy, timeout)
	if err != nil {
		return nil, err
	}
	failed := true
	defer func() {
		if failed {
			_ = connection.Close()
		}
	}()
	if err := connection.SetDeadline(time.Now().Add(timeout)); err != nil {
		return nil, err
	}
	if _, err := connection.Write([]byte{5, 1, 0}); err != nil {
		return nil, err
	}
	response := make([]byte, 2)
	if _, err := io.ReadFull(connection, response); err != nil {
		return nil, err
	}
	if response[0] != 5 || response[1] != 0 {
		return nil, fmt.Errorf("SOCKS5 proxy rejected no-auth negotiation")
	}
	host, rawPort, err := net.SplitHostPort(target)
	if err != nil {
		return nil, fmt.Errorf("parse SOCKS5 target: %w", err)
	}
	port, err := strconv.Atoi(rawPort)
	if err != nil || port < 1 || port > 65535 {
		return nil, fmt.Errorf("parse SOCKS5 target port")
	}
	request := []byte{5, 1, 0}
	if address := net.ParseIP(host); address != nil {
		if ipv4 := address.To4(); ipv4 != nil {
			request = append(request, 1)
			request = append(request, ipv4...)
		} else {
			request = append(request, 4)
			request = append(request, address.To16()...)
		}
	} else {
		if len(host) > 255 {
			return nil, fmt.Errorf("SOCKS5 target hostname is too long")
		}
		request = append(request, 3, byte(len(host)))
		request = append(request, host...)
	}
	request = binary.BigEndian.AppendUint16(request, uint16(port))
	if _, err := connection.Write(request); err != nil {
		return nil, err
	}
	header := make([]byte, 4)
	if _, err := io.ReadFull(connection, header); err != nil {
		return nil, err
	}
	if header[0] != 5 || header[1] != 0 {
		return nil, fmt.Errorf("SOCKS5 proxy rejected target with status %d", header[1])
	}
	if err := discardSOCKS5Address(connection, header[3]); err != nil {
		return nil, err
	}
	if err := connection.SetDeadline(time.Time{}); err != nil {
		return nil, err
	}
	failed = false
	return connection, nil
}

func discardSOCKS5Address(reader io.Reader, addressType byte) error {
	length := 0
	switch addressType {
	case 1:
		length = net.IPv4len
	case 3:
		size := []byte{0}
		if _, err := io.ReadFull(reader, size); err != nil {
			return err
		}
		length = int(size[0])
	case 4:
		length = net.IPv6len
	default:
		return fmt.Errorf("SOCKS5 proxy returned unknown address type %d", addressType)
	}
	remaining := make([]byte, length+2)
	_, err := io.ReadFull(reader, remaining)
	return err
}
