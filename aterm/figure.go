package main

import (
	"math"
	"strings"
)

const (
	figureWidth  = 9
	figureHeight = 5
)

type figureCell struct {
	X, Y  int
	Glyph rune
}

// plotFigure reads `form.geometry` as the <arrangement>-<shape> instruction it
// already is, so an unshipped value still composes.
func plotFigure(geometry string) []figureCell {
	arrangement, shape := splitGeometry(geometry)
	place := arrangementField(arrangement)
	ink := shapeGlyph(shape)
	cells := []figureCell{}
	for y := 0; y < figureHeight; y++ {
		for x := 0; x < figureWidth; x++ {
			dx, dy := figureOffset(x, y)
			if !place(dx, dy) {
				continue
			}
			cells = append(cells, figureCell{X: x, Y: y, Glyph: ink(dx, dy)})
		}
	}
	return cells
}

// A terminal cell is about twice as tall as it is wide, so horizontal offsets
// are halved before any radius or angle is taken.
func figureOffset(x, y int) (float64, float64) {
	return float64(x-figureWidth/2) / 2, float64(y - figureHeight/2)
}

func splitGeometry(geometry string) (string, string) {
	parts := strings.Split(strings.ToLower(strings.TrimSpace(geometry)), "-")
	if len(parts) < 2 {
		return strings.Join(parts, "-"), ""
	}
	return strings.Join(parts[:len(parts)-1], "-"), parts[len(parts)-1]
}

func arrangementField(arrangement string) func(float64, float64) bool {
	switch arrangement {
	case "radial":
		return func(dx, dy float64) bool {
			if dx == 0 && dy == 0 {
				return true
			}
			angle := math.Atan2(dy, dx)
			for spoke := 0; spoke < 6; spoke++ {
				want := -math.Pi + float64(spoke)*math.Pi/3
				if math.Abs(math.Remainder(angle-want, 2*math.Pi)) < 0.32 {
					return true
				}
			}
			return false
		}
	case "stacked":
		return func(dx, dy float64) bool {
			return math.Abs(dx) <= (dy+float64(figureHeight/2))/2
		}
	case "interlocking":
		return func(dx, dy float64) bool { return math.Abs(math.Abs(dx)-math.Abs(dy)) < 0.6 }
	case "enclosing":
		return func(dx, dy float64) bool {
			radius := math.Hypot(dx, dy)
			return radius > 1.4 && radius < 2.6 && dy < 1.5
		}
	case "nested":
		return func(dx, dy float64) bool {
			radius := math.Hypot(dx, dy)
			return radius < 0.4 || (radius > 0.9 && radius < 1.4) || (radius > 1.9 && radius < 2.4)
		}
	case "graduated":
		return func(dx, dy float64) bool {
			return math.Abs(dx) < 0.3 || (int(dy)%2 == 0 && dx > 0 && dx < 1.6)
		}
	case "extending":
		return func(dx, dy float64) bool { return math.Abs(dx) <= 0.5+dy }
	case "clean":
		return func(dx, dy float64) bool { return math.Abs(dx-dy) < 0.6 }
	case "soft":
		return func(dx, dy float64) bool {
			radius := math.Hypot(dx/1.15, dy/1.6)
			return radius > 0.72 && radius < 1.34
		}
	// Dabs land irregularly and the mask still has to be deterministic, so the
	// scatter is a lattice with a hole in it rather than a random draw.
	case "scattered":
		return func(dx, dy float64) bool {
			x, y := int(dx*2)+figureWidth/2, int(dy)+figureHeight/2
			return (x*3+y*7)%4 != 0 && math.Hypot(dx, dy) < 2.4
		}
	default:
		// An arrangement nobody has shipped yet still draws something, rather
		// than leaving a role with a blank card.
		return func(dx, dy float64) bool { return math.Hypot(dx, dy) < 1.6 }
	}
}

func shapeGlyph(shape string) func(float64, float64) rune {
	stroke := func(dx, dy float64) rune {
		switch {
		case dy == 0:
			return '─'
		case dx == 0:
			return '│'
		case dx*dy < 0:
			return '╱'
		default:
			return '╲'
		}
	}
	quadrant := func(dx, dy float64) rune {
		switch {
		case dy < 0 && dx < 0:
			return '◜'
		case dy < 0:
			return '◝'
		case dx < 0:
			return '◟'
		default:
			return '◞'
		}
	}
	switch shape {
	case "spokes", "lines", "diagonal":
		return stroke
	case "arcs", "shells", "ovals", "rounds":
		return quadrant
	case "facets":
		return func(dx, dy float64) rune {
			if dx*dy < 0 {
				return '◤'
			}
			return '◥'
		}
	case "column":
		return func(dx, _ float64) rune {
			if math.Abs(dx) < 0.3 {
				return '║'
			}
			return '─'
		}
	case "barrels":
		return func(float64, float64) rune { return '═' }
	case "dabs":
		return func(dx, dy float64) rune {
			if math.Hypot(dx, dy) < 1.2 {
				return '●'
			}
			return '◍'
		}
	default:
		return func(float64, float64) rune { return '▪' }
	}
}

// motifStipple gives each motif its own background texture. The palette is
// indexed by a stable hash, so a motif nobody has shipped yet gets one too.
func motifStipple(motif string) rune {
	palette := []rune{'·', '˖', '⋅', '∙', '‧', '⠂', '⠄', '˙'}
	if strings.TrimSpace(motif) == "" {
		return ' '
	}
	sum := 0
	for _, character := range motif {
		sum = sum*31 + int(character)
	}
	if sum < 0 {
		sum = -sum
	}
	return palette[sum%len(palette)]
}
