package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/url"

	_ "modernc.org/sqlite"
)

// storageRow is one decoded generic_string_objects row. Warp keeps every
// settings value as a JSON blob in the `data` column.
type storageRow struct {
	id       int64
	Key      string `json:"storage_key"`
	Value    any    `json:"value"`
	Platform string `json:"platform"`
}

// warpDB wraps the Warp SQLite database (state layer 3). Warp holds the file
// open in WAL mode while running; a busy_timeout lets a momentary write lock
// from Warp retry instead of erroring.
type warpDB struct {
	db *sql.DB
}

// openWarpDB opens warp.sqlite. readonly=true is used by `doctor`; `apply`
// opens read-write. Either way a 5s busy_timeout is set.
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
			continue // skip rows that are not the standard settings shape
		}
		if r.Key == storageKey {
			r.id = id
			return &r, nil
		}
	}
	return nil, rows.Err()
}

// set writes value for storageKey, updating the existing row or inserting a
// new one. platform defaults to "Global" for fresh rows.
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

// MarshalJSON keeps the storage_key/value/platform field order Warp uses.
func (r storageRow) MarshalJSON() ([]byte, error) {
	return json.Marshal(map[string]any{
		"storage_key": r.Key,
		"value":       r.Value,
		"platform":    r.Platform,
	})
}
