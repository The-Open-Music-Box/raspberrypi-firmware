---
title: "UI Design Charter"
status: active
category: guide
last_reviewed: 2026-02-09
review_cycle: 12months
---

# UI Design Charter - Universal & Multiplatform

This design charter is designed to ensure **consistency, accessibility, and portability** across all platforms and frameworks (Web, Mobile, Desktop). It defines colors, typography, UI components, and their states in a generic, adaptable format.

---

## Color Palette

### Main Palette

| Name | Hex | Role |
|------|-----|------|
| Petrol Blue | `#264C6E` | Anchor color, depth, trust |
| Soft Coral | `#F27B70` | Primary accent, emotion, warmth |
| Sage Green | `#A3C9A8` | Secondary color, calm and nature |
| Pastel Yellow | `#FFD882` | Light accent, brightness, joy |
| Ivory Beige | `#FDF8EF` | Neutral background, paper, softness |

### Light & Dark Modes

| UI Element | Light Mode | Dark Mode | Description |
|-----------|------------|-----------|-------------|
| Primary | `#F27B70` | `#F58C82` | Primary accent |
| Secondary | `#A3C9A8` | `#ADCBB3` | Secondary accent |
| Tertiary | `#FFD882` | `#FFEBA6` | Light accent / badges |
| Background | `#FDF8EF` | `#1F1F1F` | Main background |
| Surface | `#FFFFFF` | `#2A2A2A` | Component background |
| On Primary | `#FFFFFF` | `#1F1F1F` | Text on primary |
| On Background | `#3A3A3A` | `#F1F1F1` | Main text |
| On Surface | `#444444` | `#E0E0E0` | Secondary text |
| Border / Divider | `#DADADA` | `#555555` | Separators |
| Error | `#D9605E` | `#F58C8A` | Critical alert |
| Success | `#77C29B` | `#93D1B1` | Validation |
| Disabled | `#C5C5C5` | `#707070` | Inactive |
| Focus / Outline | `#6F9FD2` | `#99BFF2` | Visible focus |

---

## Typography

| Usage | Primary Font | Alternatives | Recommended Weights |
|-------|-------------|-------------|-------------------|
| Headings | Nunito Sans, Baloo 2 | Poppins, Raleway | 600-800 |
| Body Text | Figtree, DM Sans | Inter, Open Sans | 400-600 |
| Technical | JetBrains Mono | Rubik Mono One | 400-500 |

- **Minimum size**: 14px
- **Recommended body text size**: 16px
- **Contrast**: Follows WCAG AA/AAA

---

## Design Tokens (Abstract)

```yaml
color:
  primary: "#F27B70"
  onPrimary: "#FFFFFF"
  secondary: "#A3C9A8"
  surface: "#FFFFFF"
  background: "#FDF8EF"
  onSurface: "#444444"
  error: "#D9605E"
  success: "#77C29B"
  focus: "#6F9FD2"
  disabled: "#C5C5C5"
```

---

## UI Components

### Navigation

- AppBar: `background`, text `onBackground`, shadow on scroll
- Bottom Navigation: `primary` (selected), `onSurface` (inactive)
- Drawer: `surface` background, active text `secondary`
- TabBar: Active tab `primary`, inactive `onSurface`

### Buttons

| Type | Background | Text | Hover / Focus / Disabled |
|------|-----------|------|--------------------------|
| ElevatedButton | Primary | OnPrimary | Shadow, darker color |
| OutlinedButton | Surface | Primary | `focus` border |
| TextButton | Transparent | Primary | Underlined or bold text |
| IconButton | Primary | OnPrimary | Focus circle + shadow |
| FAB | Primary | OnPrimary | Shadow + color change |

### Input Fields

- Background: `surface`
- Border: `border`
- Text: `onSurface`
- Placeholder: `disabled`
- Error text: `error`
- Focus state: `focus` (border or shadow)

### Lists & Cards

- Card: `surface`, text `onSurface`, light shadow
- Chip: `secondary` or `tertiary`, text `onSecondary`
- ListTile: hover `focus`, selected `primary`

### States & Alerts

| Type | Color | Text / Icon |
|------|-------|------------|
| Info | Tertiary | OnBackground |
| Success | Success | OnSurface |
| Alert | Error | OnPrimary |
| Disabled | Disabled | OnSurface 50% |
| Focus | Focus | Outline/shadow |

---

## Common UI States

- **Hover**: Light shadow or darker tint
- **Focus**: Colored outline or halo
- **Active**: More saturated color
- **Disabled**: 40-60% opacity or dedicated color
- **Selected**: Lighter `primary` or `secondary` background

---

## Accessibility

- All contrasts comply with **WCAG 2.1** level **AA** minimum, AAA for critical elements.
- Visible focus is always present (outline, shadow).
- Keyboard navigation is compatible for all interactive components.
- No animation should block comprehension or last more than 5 seconds without user control.

---

## Product Branding - (TalesTide example)

- Scanned RFID card: `tertiary` background, `focus` halo
- Sound wave: gradient from `primary` to `secondary`
- Open source badge: `success` + `primary` border
- Narration panel: `tertiary` background, text `onTertiary`

---

## Multiplatform Integration

- **Web / CSS**: via `:root { --color-primary: #F27B70; }`
- **Flutter**: `ThemeData` and `ColorScheme` Material 3
- **iOS**: UIColor with Asset Catalogs
- **Android**: XML `colors.xml`
- **React / Tailwind**: via `theme.extend.colors`

---

## Recommended Structure

```
/tokens/
  colors.yaml
  typography.yaml
/themes/
  theme.light.json
  theme.dark.json
flutter/
  lib/theme/colors.dart
web/
  styles/theme.css
```
