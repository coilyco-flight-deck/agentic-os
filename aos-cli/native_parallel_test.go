package main

import (
	"sync/atomic"
	"testing"
	"time"
)

func TestRunParallelVisitsEveryIndexOnce(t *testing.T) {
	for _, limit := range []int{0, 1, 3, 50} {
		seen := make([]int32, 20)
		runParallel(len(seen), limit, func(index int) { atomic.AddInt32(&seen[index], 1) })
		for index, count := range seen {
			if count != 1 {
				t.Fatalf("limit %d: index %d ran %d times", limit, index, count)
			}
		}
	}
	runParallel(0, 4, func(int) { t.Fatal("no work was asked for") })
}

func TestRunParallelNeverExceedsTheLimit(t *testing.T) {
	var running, peak int32
	runParallel(24, 3, func(int) {
		now := atomic.AddInt32(&running, 1)
		for {
			seen := atomic.LoadInt32(&peak)
			if now <= seen || atomic.CompareAndSwapInt32(&peak, seen, now) {
				break
			}
		}
		time.Sleep(5 * time.Millisecond)
		atomic.AddInt32(&running, -1)
	})
	if peak > 3 || peak < 2 {
		t.Fatalf("peak concurrency %d, want 2 or 3 under a limit of 3", peak)
	}
}

func TestRunParallelOfOneKeepsSerialOrder(t *testing.T) {
	var order []int
	runParallel(6, 1, func(index int) { order = append(order, index) })
	for index, got := range order {
		if got != index {
			t.Fatalf("serial order broken: %v", order)
		}
	}
}

func TestNativeParallelLimitFallsBackOnBadInput(t *testing.T) {
	for raw, want := range map[string]int{
		"": nativeParallelDefault, "abc": nativeParallelDefault, "0": nativeParallelDefault,
		"-2": nativeParallelDefault, "1": 1, " 4 ": 4,
	} {
		t.Setenv(nativeParallelEnv, raw)
		if got := nativeParallelLimit(); got != want {
			t.Errorf("%q: got %d, want %d", raw, got, want)
		}
	}
}
