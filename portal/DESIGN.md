# VedicAstro Portal — Design System & Taste Record

The decisions are made here, once, so the UI never drifts back to the generic
"AI-template" look (purple gradient, everything centered, soft drop-shadows, a
font nobody chose). Append a rule every time the design drifts. This file is the
heavy lifter — read it before changing any UI.

## Identity

Premium, calm, precise, culturally resonant — a serious instrument, not a toy.
Dark-first but light-capable. The accent is rare, which is why it lands.

## Tokens (source of truth: `src/app/globals.css`)

**Color** — semantic CSS vars, light + dark via `.dark`:
- `--color-primary` Deep Royal Indigo (#1e3a5f / lifted #5b86c2 dark) — structure, primary actions
- `--color-accent` Warm Gold/Saffron (#c5a46e / #d4b483 dark) — *rare* highlights only
- `--color-background`, `--color-card`, `--color-text-main`, `--color-text-muted`
- `--color-hairline` — all borders/dividers
- `--color-success / warning / danger` — verdict semantics (śubha / mixed / aśubha)

**Type** — three deliberate families (NOT the framework default):
- `--font-display` = **Fraunces** (optical serif) — all headings (`h1–h3`), the cultural/premium voice
- `--font-sans` = **Sora** — UI/body
- `--font-mono` = **JetBrains Mono** — data, labels, chart cells, degrees

**Shape** — `rounded-xl`/`2xl` for cards/inputs; hairline borders; max-width `7xl`.

## Do
- Use the **Fraunces serif** for every heading. It is the signature.
- Express elevation with **color + a 1px hairline**, never a soft shadow.
- Keep the **gold accent rare** — verdict highlights, a single CTA, the lagna cell.
- Left-align hero and content. Generous vertical rhythm (`py-10`+ sections).
- Use **JetBrains Mono** for all astronomical data (degrees, bindus, sign codes).
- Verdict color is semantic and consistent: success=śubha, warning=mixed, danger=aśubha.

## Don't
- ❌ No purple. No rainbow gradients. The wash is indigo→gold, very subtle (`.bg-aurora`).
- ❌ No `box-shadow` for elevation on cards/containers.
- ❌ Don't use the default sans (Geist/system) for headings — headings are serif.
- ❌ Don't center long body copy or stack everything centered.
- ❌ No arbitrary hex in components — only the semantic tokens.
- ❌ Don't let the gold accent become a background or fill large areas.

## Components
- `ui/Button` — `primary` (indigo), `accent` (gold, sparing), `ghost` (hairline).
- `ui/Card` — `bg-card` + hairline, no shadow.
- `chart/KundaliChart` — prop-driven SVG, South/North, renders any varga from `chart_data`.
- `chart/ChartViewer` — N/S toggle, D1–D60 selector, SAV overlay, planet table.

## Drift log
_Append each correction here (date — rule). Example:_
- 2026-06-24 — Replaced default Geist headings with Fraunces serif; removed card drop-shadows (elevation via color), per the "looks AI-generated" review.
