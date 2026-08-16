---
name: Privacy Guard
description: Local Sanitize/Restore landing (Persuade) and Operate dashboard as a separate surface.
colors:
  paper: "#f5f5f7"
  ink: "#1d1d1f"
  muted: "#424245"
  blue: "#0071e3"
  chip: "#fbfbfd"
  placeholder: "#6e388c"
  shadow-soft: "rgba(0, 0, 0, 0.06)"
  shadow-code: "rgba(0, 0, 0, 0.12)"
  dash-paper: "#14110e"
  dash-ink: "#f3eadc"
  dash-oxide: "#e07048"
typography:
  display:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(2.4rem, 6vw, 4.75rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.035em"
  section:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  lede:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "-0.01em"
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.47
    letterSpacing: "normal"
  demo:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.55
  nav:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.92rem"
  caption:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.8rem"
  code:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "0.86rem"
  footer:
    fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.88rem"
rounded:
  pill: "980px"
  panel: "1.15rem"
  pre: "0.85rem"
  chip: "0.28rem"
  code: "0.3rem"
spacing:
  gutter: "6vw"
  section: "4.5rem"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0 1.15rem"
---

# Design System

Two surfaces, two worlds. Do not mix them.

## Brand & Visual Identity

**Landing (`web/`)** — Persuade. Fluorescent hall + laptop. Apple materials: system type, `#f5f5f7` paper, `#1d1d1f` ink, pill CTA `#0071e3`, translucent sticky nav. Brief-pinned; not the dashboard job ticket.

**Dashboard (`src/privacy_guard_agent/dashboard.html`)** — Operate. Night-ink ledger on charcoal. Hero is the count of distinct values kept off Featherless. Hairline rules, dotted category leaders. Stay off the landing.

## Color

Landing is restrained: neutrals plus one blue for action. Placeholders in the synthetic demo use `#6e388c` so they read as typed, not as links. Dashboard oxide `#e07048` is Operate-only.

## Typography

System UI stack on both. Landing display is large, tight tracking, weight 600. Body ~65ch. Dashboard display is the numeric hero (max 6rem), tabular nums.

## Components

Landing primary control is a full-pill CTA. Feedback on pointer-down (`scale(0.97)`, 100ms). Nav is heavier glass; CTA is solid. Do not stack light glass on light glass.

## Layout

Landing: sticky nav, hero with one H1 (no eyebrow), synthetic sanitize demo, then Install / Use / Limits as stacked sections — not a grid of equal icon cards.

Dashboard: job ticket. Product name and channel slugline on a top rule. Count as heading. Category leaders. Status footer.

## Depth & Materials

Landing nav: `backdrop-filter: blur(20px) saturate(180%)` plus translucent fill. Panels: 8px-offset soft shadow, not a zero-offset glow. Reduced-transparency drops the blur.

## Motion

One authored moment on the landing: Channel Message secrets cross-fade/blur into Placeholders (380ms, cubic-bezier 0.22, 1, 0.36, 1). Same path back. `prefers-reduced-motion` removes the blur. Dashboard polls `/stats.json` every 2s with no entrance choreography.

## Imagery

No photos, no customer logos. The demo sentence is labeled synthetic. Dashboard shows counts only.
