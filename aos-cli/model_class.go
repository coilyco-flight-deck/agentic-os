package main

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"strings"
)

const layoutModelClassesFormat = "agentic-os.layout-model-classes.v1"

//go:embed layout-model-classes.json
var embeddedLayoutModelClasses []byte

type layoutModelClassesDocument struct {
	Format  string            `json:"format"`
	Layouts map[string]string `json:"layouts"`
}

func loadLayoutModelClasses(data []byte) (map[string]string, error) {
	var document layoutModelClassesDocument
	decoder := json.NewDecoder(strings.NewReader(string(data)))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&document); err != nil {
		return nil, fmt.Errorf("decode layout model classes: %w", err)
	}
	if err := ensureJSONEnd(decoder); err != nil {
		return nil, fmt.Errorf("decode layout model classes trailer: %w", err)
	}
	if document.Format != layoutModelClassesFormat {
		return nil, fmt.Errorf("unsupported layout model class format %q", document.Format)
	}
	if len(document.Layouts) == 0 {
		return nil, fmt.Errorf("layout model class registry is empty")
	}
	for layout, modelClass := range document.Layouts {
		if strings.TrimSpace(layout) == "" {
			return nil, fmt.Errorf("layout model class registry contains an empty layout")
		}
		if modelClass != "frontier" && modelClass != "low-context" {
			return nil, fmt.Errorf("layout %q has unsupported model class %q", layout, modelClass)
		}
	}
	return document.Layouts, nil
}

func modelClassForLayout(layout string) (string, error) {
	layouts, err := loadLayoutModelClasses(embeddedLayoutModelClasses)
	if err != nil {
		return "", err
	}
	modelClass, ok := layouts[layout]
	if !ok {
		return "", fmt.Errorf("unsupported AOS layout %q", layout)
	}
	return modelClass, nil
}
