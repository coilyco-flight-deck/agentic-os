package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"

	_ "modernc.org/sqlite"
)

// storageRow is one decoded generic_string_objects row (JSON in `data`).
type storageRow struct {
	id       int64
	Key      string `json:"storage_key"`
	Value    any    `json:"value"`
	Platform string `json:"platform"`
}

// warpDB wraps warp.sqlite. WAL mode plus a 5s busy_timeout.
type warpDB struct {
	db *sql.DB
}

func openWarpDB(path string, readonly bool) (*warpDB, error) {
	dsn := "file:" + url.PathEscape(path) + "?_pragma=busy_timeout(5000)"
	if readonly {
		dsn += "&mode=ro"
	}
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("opening warp.sqlite: %w", err)
	}
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("opening warp.sqlite at %s: %w", path, err)
	}
	return &warpDB{db: db}, nil
}

func (w *warpDB) Close() error { return w.db.Close() }

// hasStorageTable reports whether the generic_string_objects table exists.
// A fresh or never-launched warp.sqlite has none, so missing = "not ready", not fatal.
func (w *warpDB) hasStorageTable() (bool, error) {
	var name string
	err := w.db.QueryRow(
		"SELECT name FROM sqlite_master WHERE type='table' AND name='generic_string_objects'",
	).Scan(&name)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("checking for generic_string_objects: %w", err)
	}
	return true, nil
}

// get returns the generic_string_objects row for a storage_key, if present.
func (w *warpDB) get(storageKey string) (*storageRow, error) {
	rows, err := w.db.Query("SELECT id, data FROM generic_string_objects")
	if err != nil {
		return nil, fmt.Errorf("querying generic_string_objects: %w", err)
	}
	defer rows.Close()
	for rows.Next() {
		var id int64
		var data string
		if err := rows.Scan(&id, &data); err != nil {
			return nil, err
		}
		var r storageRow
		if err := json.Unmarshal([]byte(data), &r); err != nil {
			continue
		}
		if r.Key == storageKey {
			r.id = id
			return &r, nil
		}
	}
	return nil, rows.Err()
}

// set upserts value for storageKey. New rows default platform to "Global".
func (w *warpDB) set(storageKey string, value any) error {
	existing, err := w.get(storageKey)
	if err != nil {
		return err
	}
	platform := "Global"
	if existing != nil && existing.Platform != "" {
		platform = existing.Platform
	}
	blob, err := json.Marshal(storageRow{Key: storageKey, Value: value, Platform: platform})
	if err != nil {
		return err
	}
	if existing != nil {
		_, err = w.db.Exec("UPDATE generic_string_objects SET data = ? WHERE id = ?", string(blob), existing.id)
	} else {
		_, err = w.db.Exec("INSERT INTO generic_string_objects (data) VALUES (?)", string(blob))
	}
	if err != nil {
		return fmt.Errorf("writing %s to warp.sqlite: %w", storageKey, err)
	}
	return nil
}

// MarshalJSON keeps Warp's storage_key/value/platform field order.
func (r storageRow) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]any{
		"storage_key": r.Key,
		"value":       r.Value,
		"platform":    r.Platform,
	})
}
