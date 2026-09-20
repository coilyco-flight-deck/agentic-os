package main

import (
	"os"
	"strconv"
	"strings"
	"sync"
)

const (
	// nativeParallelEnv caps concurrent Git jobs per startup phase, and 1 makes
	// them serial. docs/native-session-start.md
	nativeParallelEnv     = "AOS_NATIVE_PARALLEL"
	nativeParallelDefault = 8
)

// nativeParallelLimit reads the cap, falling back to the default on anything
// that is not a positive integer.
func nativeParallelLimit() int {
	limit, err := strconv.Atoi(strings.TrimSpace(os.Getenv(nativeParallelEnv)))
	if err != nil || limit < 1 {
		return nativeParallelDefault
	}
	return limit
}

// runParallel runs work(index) for each index in [0, count) on at most limit
// goroutines. work writes only its own index of any shared slice.
func runParallel(count, limit int, work func(index int)) {
	if limit > count {
		limit = count
	}
	if limit <= 1 {
		for index := 0; index < count; index++ {
			work(index)
		}
		return
	}
	indexes := make(chan int)
	var group sync.WaitGroup
	for worker := 0; worker < limit; worker++ {
		group.Add(1)
		go func() {
			defer group.Done()
			for index := range indexes {
				work(index)
			}
		}()
	}
	for index := 0; index < count; index++ {
		indexes <- index
	}
	close(indexes)
	group.Wait()
}
