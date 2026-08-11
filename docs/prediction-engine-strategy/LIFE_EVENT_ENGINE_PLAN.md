# Life-Event Prediction Engine — v1 Implementation Plan

**Status:** design, not started. Spec seed: `docs/VEDIC_DIGEST_METHOD_AUDIT.md` (deviations D1–D6).
**Owner mandate (2026-07-17):** event-first dated windows a visitor can check against their own
life — "did the app correctly predict my marriage date / my kid's birth / my international job?"
— surfaced on the Person Timeline with a one-tap resolution and a visible per-chart accuracy tally.
This is the product's trust engine, not a feature among many.

---

## 0. The one-sentence architecture

Replace `_priority_predictions`' yoga-ranking with an **event-domain evaluator**: for each of six
life-event domains, test the natal promise via six witnesses → confidence tier → find dasha windows
whose lords are *connected* to the event's house network (not just "the yoga planet's MD") →
narrow with `fructify()` → emit as `engine_inference` timeline milestones with a new `life_event.*`
canonical-id family, honestly labelled as non-prospective, resolvable the same way observed events
are today.

No timeline contract changes. No new `MilestoneOrigin` value. No schema migration.

---

## 1. Event domain registry v1

**Reuse, don't duplicate.** `cvce/app/rectification.py:49-57` already has a `DOMAIN_HOUSES` table
(marriage, children, career_status, career_obstacle, mother, father, death_loss) with a working
`_domain_significators(domain, lagna_idx)` helper (`rectification.py:70-75`) that resolves house
lordship *per candidate lagna* — exactly the "not a one-size-fits-all karaka guess" discipline the
audit's D1 demands. Extract the shared parts into a new module both consumers import:

**New file: `cvce/vedic_engine/prediction/life_event_domains.py`**
```python
RASHIS = [...]          # move from rectification.py:35-38
SIGN_LORDS = {...}      # move from rectification.py:40-44

DOMAIN_REGISTRY: dict[str, "EventDomain"] = {
    "marriage":        EventDomain(houses=[7],      karakas=["Venus"],           varga=9,  label="Marriage"),
    "children":        EventDomain(houses=[5],       karakas=["Jupiter"],         varga=7,  label="Childbirth"),
    "career_rise":     EventDomain(houses=[10],       karakas=["Sun", "Saturn", "Mercury"], varga=10, label="Career rise"),
    "foreign_move":    EventDomain(houses=[12, 3, 9], karakas=["Rahu"],           varga=12, label="Foreign move"),  # p15 high-specificity map
    "home_acquisition":EventDomain(houses=[4],       karakas=["Moon", "Mars"],    varga=4,  label="Home / property"),
    "health_episode":  EventDomain(houses=[1, 6, 8, 12], karakas=[],              varga=6,  label="Health episode"),
}
```
(`EventDomain` a small frozen dataclass/NamedTuple: houses, karakas, varga, label, corroborating
houses per audit's high-specificity map p15 — e.g. marriage also checks 2/8/11 per the notes'
"context" column.)

`rectification.py` keeps `career_obstacle`, `mother`, `father`, `death_loss` as rectification-only
domains (its own purpose — matching *known* events to find birth time — is broader than the
predictive six above) but imports `RASHIS`/`SIGN_LORDS`/`_house_lord` from the new shared module
instead of defining its own copies. `_domain_significators` moves too, generalized to accept the
new `EventDomain` shape; rectification's call sites (`rectification.py:145,157`) adapt trivially.

**Finance/health split note:** the audit's Domain Keys table (D1) lists Finance (2/11) separately
from Health (1/6/8/12). v1 ships Health only (matches the audit's high-specificity map p15, which
gives Health a full witness/varga/endpoint spec); Finance is a v1.1 addition — same registry
pattern, no architecture change, deferred only to keep the first slice small.

---

## 2. Witness evaluation — the six-witness algorithm (D4, D6)

**New file: `cvce/vedic_engine/prediction/life_event_witness.py`**

Inputs already computed in `build_report_facts` (`report_facts.py:492-534`): `geometry.planets`
(rashi/degree per planet), `geometry.lagna`, `natal_sign` dict, and the varga sign maps available
via `_varga_sign_map(jd, place, dcf)` (`chart.py:39-53`, currently only called for D1/D9 in
`build_chart_geometry` — v1 must request the domain's specific varga too, e.g. D10 for career,
D7 for children; extend the `vargas` param passed to `build_chart_geometry` per-domain-evaluation
rather than the fixed `settings.VARGAS[:2]`).

```python
def evaluate_witnesses(domain: EventDomain, lagna_idx: int, planet_signs: dict[str, int],
                        varga_sign_map: dict[str, int]) -> WitnessReport:
    witnesses = []
    house_lord = _house_lord(lagna_idx, domain.houses[0])          # rectification.py pattern
    witnesses.append(Witness("house_lord", house_lord, present=True))  # lordship always "present" — it's structural
    occupants = [p for p, s in planet_signs.items()
                 if _planet_house(s, lagna_idx) in domain.houses]  # yoga.py:659-662 pattern
    for p in occupants:
        witnesses.append(Witness("occupant", p, present=True))
    for karaka in domain.karakas:
        witnesses.append(Witness("karaka", karaka, present=karaka in planet_signs))
    # varga confirmation (D6): domain varga's lagna lord / house lord agrees with D1
    varga_lord_matches = _varga_confirms(domain, varga_sign_map)
    witnesses.append(Witness("varga", f"D{domain.varga}", present=varga_lord_matches))
    # yoga corroboration: any detect_yogas() result whose category/planets overlap this domain
    witnesses.append(Witness("yoga", ..., present=bool(matching_yogas)))
    return WitnessReport(witnesses=witnesses, confidence=_confidence_tier(witnesses))

def _confidence_tier(witnesses: list[Witness]) -> str:
    n = sum(1 for w in witnesses if w.present)
    return "low" if n <= 1 else "medium" if n == 2 else "high"   # audit p10: 1=clue, 2=theme, 3+=usable
```

**Stability gate (D5):** reuse the exact pattern already proven in `rectification.py` — recompute
at birth time ± 2 minutes (configurable), rerun `evaluate_witnesses`, and only report `confidence`
at face value if the house-lord identity and varga-lord identity are unchanged across all three
recomputations; otherwise downgrade one tier and append the notes' exact language: *"This claim
depends on birth-time precision narrower than what's on record — treat the window as approximate."*
This does **not** require new ephemeris code — it's three calls to the same
`build_chart_geometry`/`ascendant` pipeline already used everywhere, at `birth_datetime ± Δ`.

---

## 3. Window generation — lord-chain gating (D2) + transit narrowing (D3)

**Lord-chain connectivity** — the audit's "read the lord chain": an MD or AD lord *qualifies* a
window only if it is connected to the event's house network by at least one of:

1. **Lordship** — the dasha lord *is* the event's house lord (already have this).
2. **Occupation** — the dasha lord sits *in* one of the event's houses (`yoga.py:659-662`
   `_planet_in_house`, reusable directly).
3. **Aspect** — the dasha lord aspects the event's house lord or an occupant. PyJHora exposes this
   natively: `jhora.horoscope.chart.house.planets_aspecting_the_planet` /
   `graha_drishti_of_the_planet` (confirmed available, not yet imported anywhere in this repo —
   `cvce/app/ephem.py` is the only file that imports PyJHora directly per `CONTEXT.md`'s guardrail,
   so this wrapper belongs there: `ephem.py` gains `aspects_between(jd, place, planet_a, planet_b) -> bool`).
4. **Dispositor chain** — the dasha lord's own dispositor (sign lord of the sign it occupies) is
   the event's house lord or a karaka (`_sign_lord`, `yoga.py:678-682`, already exists).

```python
def qualifies(dasha_lord: str, domain_witnesses: WitnessReport, planet_signs: dict, lagna_idx: int) -> bool:
    return (dasha_lord == domain_witnesses.house_lord
            or _planet_in_house(domain.houses[0], lagna_idx, planet_signs[dasha_lord])
            or aspects_between(..., dasha_lord, domain_witnesses.house_lord)
            or _sign_lord(RASHIS[planet_signs[dasha_lord]]) in {domain_witnesses.house_lord, *domain.karakas})
```

**Selection order** (mirrors `mahadasha_tree`'s existing structure, `dasha_vimshottari.py:203-284`
— no new dasha computation, just a filter pass over its output):
1. Walk the MD list; keep MDs where `qualifies(md_lord, ...)`.
2. Within each qualifying MD, walk `subPeriods` (ADs); keep ADs where `qualifies(ad_lord, ...)`.
   An MD with zero qualifying ADs is still reported at MD-only resolution (native_resolution=YEAR)
   rather than dropped — the notes' "if any essential gate is zero, confidence must fall," not
   "the whole window vanishes."
3. **PD only inside a qualified AD** (audit's explicit rule) — call `dasha_deep_payload(jd, place,
   max_level=3, deep_antar_path=(md_id, ad_id))` (`dasha_vimshottari.py:287+`, already supports a
   targeted deep path) only for AD windows that both qualify *and* have `confidence >= "medium"`,
   to bound cost.

**Transit narrowing (D3):** for each qualifying AD (not all — audit explicitly flags this as the
"few windows, not 40 yogas" cost control, already the pattern used for the existing yoga
priority list), call the existing `fructify()` (`fructification.py:407-419`) with that AD's
`maha_lord`, `antar_lord`, and date range. Its return already includes month-level windows scored
against Ashtakavarga SAV (`compute_ashtakavarga` inside `fructify`) — no new AKV code needed, just
wiring the call. Store the fructification windows as the milestone's `peak_at` candidates rather
than replacing the AD-level window (preserve native resolution honesty per `narration.py`'s
existing `temporal_precision_text` pattern).

---

## 4. API shape

**Extend `report_facts.py`, don't add a new top-level endpoint.** Add a sibling to
`_priority_predictions` (`report_facts.py:360`):

```python
def _life_event_predictions(geometry, jd, place, planets, lagna, today_str, domains=None) -> list[dict]:
    """One entry per domain in DOMAIN_REGISTRY (or the requested subset)."""
    for key, domain in (domains or DOMAIN_REGISTRY).items():
        witnesses = evaluate_witnesses(domain, lagna_idx, planet_signs, varga_sign_map)
        if witnesses.confidence == "low" and not INCLUDE_LOW_CONFIDENCE:
            continue   # audit: "no combination = no conclusion"
        windows = qualifying_dasha_windows(domain, witnesses, jd, place)
        for window in windows:
            fructified = fructify(...) if window.confidence != "low" else None
            yield {
                "domain": key,
                "label": domain.label,
                "witnesses": witnesses.as_dicts(),
                "confidence": witnesses.confidence,
                "window": {"start": window.start, "end": window.end, "peak": fructified and fructified["peak"]},
                "output_template": build_output_template(domain, witnesses, window),  # §5 below
            }
```
Wire into `build_report_facts` (`report_facts.py:813-823`, alongside the existing
`priority_predictions` block) as `"life_event_predictions": life_event_predictions`, gated by a
new `include_life_events: bool = True` param matching the existing `include_*` flag pattern.

**Timeline integration** — `research_engine/timeline/service.py`'s `query()` method
(`service.py:228-311`) currently iterates only `facts.get("priority_predictions")`
(`service.py:283`). Add a parallel loop over `facts.get("life_event_predictions")` calling a new
`_life_event_candidate(...)` sibling to `_legacy_candidate` (`service.py:377-522`), with:
- `origin_record_id = f"life-event:{domain_key}:{window_index}"`
- `canonical_event_id = f"life_event.{domain_key}"` (a **new family**, not `legacy.yoga_activation.*`
  — this is the key discriminator the portal UI uses to render these as headline event cards
  rather than yoga-activation research rows)
- `origin = MilestoneOrigin.ENGINE_INFERENCE` (no contract change)
- `direction` from the domain's net favourability (reuse the `benefic`-flag plumbing shipped
  2026-07-17: `report_facts.py`'s enrichment loop already tags yoga `benefic`; extend the same
  tagging to whichever yoga corroborates a life-event witness)
- New narration helpers in `narration.py` alongside `legacy_candidate_statement`/
  `legacy_identity_notice`:
  ```python
  def life_event_identity_notice() -> str:
      return ("Chart-based research estimate for this life-event window. It was not sealed "
              "before any outcome and is not a validated forecast — check it against what "
              "actually happened using the button below.")
  ```

**No new HTTP endpoint required** — `/report/facts` and `/timeline/query` already carry this once
wired, matching the existing shipped architecture exactly.

---

## 5. Output template (verbatim per the audit, p10)

Every life-event prediction's `output_template` field is a small dict rendered directly in the UI,
not free prose:
```json
{
  "event": "Marriage — legal registration or equivalent commitment, by Nov 2002",
  "reason": "7th house (Aquarius) lord Saturn; Venus (karaka) in 7th; D9 lagna lord agrees; Vimshottari Venus MD, Saturn AD activates 7th-lord network",
  "manifestation": "Likely through a formal introduction or family-arranged process, first signalled by a serious relationship conversation",
  "confidence": "high",
  "confidence_reason": "4 independent witnesses: house lord, karaka occupant, varga confirmation, yoga corroboration",
  "alternatives": "A significant long-term partnership commitment without formal registration fits the same symbolism",
  "limits": "Depends on recorded birth time accuracy (±2min stability: stable); not a guarantee — a promise with dasha support, not proof"
}
```
This is a direct transcription of the notes' mandated template (p10) — do not paraphrase it away
in implementation; the fields map 1:1 to `event/reason/manifestation/confidence/alternatives/limits`.

---

## 6. Portal UX

**Digest (`TimelineDigest.tsx`):** life-event predictions with `canonical_event_id` starting
`life_event.` get priority placement in "Opening ahead" / "Active now" columns — sorted before
generic `legacy.yoga_activation.*` entries, since these are the headline claims users came for.

**Canvas/List:** unchanged rendering path (already origin/valence-driven from the 2026-07-17
redesign) — life-event milestones are visually identical in kind to today's research candidates
(dotted border, valence colour), just carry richer `title`/`description` text built from §5's
template instead of a yoga name. `MilestoneDetailSheet.tsx`'s existing evidence sections
(`supportingEvidence`/`opposingEvidence`) map directly onto the witness list from §2 — supporting =
present witnesses, opposing = absent-but-checked witnesses (the audit's "state both sides").

**One-tap resolution — the actual trust mechanic.** Current gate in `MilestoneDetailSheet.tsx`
(`milestone.origin === "prospective_prediction"` renders `OutcomeResolutionForm`, else a static
"only a sealed prediction can be scored" message) **must be extended**: life-event `engine_inference`
milestones need the same hit/partial/miss/false-alarm control. This is a deliberate, labelled
exception — add a second condition: `milestone.canonical_event_id?.startsWith("life_event.")` also
renders `OutcomeResolutionForm`, but the sheet's copy must say (new banner, not the existing
`legacy_identity_notice` text): *"You're checking this research estimate against something that
already happened. Because it wasn't sealed before the fact, a match here isn't prospective
proof — it tells you whether the chart's logic lands on your real dates, which is what you're here
to find out."* This is the honest version of exactly what the owner asked for.

**Per-chart accuracy tally — new component, `TimelineAccuracyTally.tsx`.** Above or beside the
digest: *"7 of 9 life-event windows you've checked matched something that happened."* Computed
client-side from `timeline.outcomes` filtered to `status in {hit, partial_hit}` over
`predictionMilestoneId`s whose milestone `canonical_event_id` starts `life_event.`, divided by the
count of life-event milestones with *any* resolution (unresolved ones excluded from the
denominator — never pad the score with unanswered questions). Label clearly: "user-confirmed
matches on retrospective research, not a validated prospective accuracy rate" — small print, but
present, non-negotiable per the project's integrity rules.

---

## 7. Test plan

- **CVCE unit** (`cvce/tests/test_life_event_domains.py`, `test_life_event_witness.py`,
  `test_life_event_windows.py`): synthetic charts with known house-lord/aspect/dispositor
  configurations (not the Mohan golden chart alone — need charts engineered to hit each
  qualification branch in §3, plus a "zero witnesses" chart to verify graceful `confidence=low`
  suppression). Golden-chart regression: Mohan's chart (1975-04-22T19:15, Mysore) gets a
  structural assertion only (domain count, confidence tiers, window count) — no real marriage/kid/
  job dates exist in the repo to assert against, and none should be fabricated.
- **CVCE integration**: extend `test_report_priority.py` (already touched 2026-07-17 for the
  `direction` field) with `life_event_predictions` presence/shape assertions;
  `test_person_timeline_api.py` with the new `canonical_event_id` family and resolution-gate test.
- **Portal**: `timeline-view.ts` gets a pure helper for tally computation with `node --test`
  coverage (mirrors the existing `buildDigest` pattern, `timeline-view.ts:213-247`); Playwright
  interaction test for the resolution flow on a `life_event.*` milestone (extends
  `interaction.test.ts`'s existing "milestone click opens detail sheet" pattern).
- **MAFIP gate**: full cycle per project law — remediate to ≥95, zero Critical/High, before any
  deploy. Given the scientific-integrity stakes (D4/D5 language, the tally's "not validated
  accuracy" framing), the independent reviewer should specifically adversarial-test for any
  phrasing that could read as a guarantee.

---

## 8. Phasing

**v1 (this plan, one MAFIP cycle):** 5 domains (marriage, children, career_rise, home_acquisition,
health_episode) at MD/AD resolution + fructification month-narrowing; witness confidence tiers;
stability gate; output template; resolution + tally UX.

**v1.1 (follow-on, same architecture, no rework):** `foreign_move` + `finance` domains; PD-level
windows inside high-confidence qualified ADs (currently: any qualified AD is eligible — v1.1 tightens
to confidence≥high only, per cost); cross-system corroboration as a counted witness (Yogini/Chara
agreement — the audit's "minor notes" item, `docs/VEDIC_DIGEST_METHOD_AUDIT.md` bottom).

**v2 (separate mission, not scoped here):** the actual sealing/prospective-prediction workflow
(`v2/forecast/brief` endpoint already exists per `server.py:740-773` but is gated `off` by default
and produces `ForecastClaim`s, a different, stricter contract than timeline milestones) — once that
lands, `life_event.*` predictions for *future* windows can be promoted into real sealed,
timestamped forecasts, and the tally gains a genuinely prospective column alongside the
retrospective one. v1 does not block on this; it delivers the trust mechanic now with honest
labelling of what it currently is.

---

## 10. Design review + fixture prep (2026-08-11, pre-implementation — implementation itself stays gated)

**Design review verdict: still fully accurate, no plan updates needed.** Checked every file:line
citation in this doc against the codebase as it stands today, a month after this plan was written
(and after a month of unrelated B-16/knowledge-engine/self-evolving-memory/Vercel-migration work
landing elsewhere). Every citation matched exactly or within a few lines: `DOMAIN_HOUSES`/
`_domain_significators`/`RASHIS`/`SIGN_LORDS`/`_house_lord` in `rectification.py`,
`_varga_sign_map` in `chart.py`, `_planet_in_house`/`_sign_lord` in `yoga.py` (both landed on the
exact cited line), `mahadasha_tree`/`dasha_deep_payload` in `dasha_vimshottari.py` (exact),
`fructify` in `fructification.py` (exact), `query()`/`_legacy_candidate`/
`facts.get("priority_predictions")` in `timeline/service.py` (exact), `legacy_candidate_statement`/
`legacy_identity_notice` in `narration.py`, the `milestone.origin === "prospective_prediction"`
gate in `MilestoneDetailSheet.tsx`, `buildDigest` in `timeline-view.ts`. Only the
`report_facts.py` wiring point drifted (§4 cited 813-823; `"priority_predictions"` now wires at
891 — other work landed in between). None of this plan's target files were touched by the past
month's other work.

**One real gap found — resolve before implementing, not after.** §2's witness pseudocode for
karaka presence — `Witness("karaka", karaka, present=karaka in planet_signs)` — is vacuous as
literally written: `planet_signs` always contains all 9 grahas for any natal chart, so this
specific check is `True` unconditionally, for every chart, every domain. The audit doc
(`VEDIC_DIGEST_METHOD_AUDIT.md`) almost certainly has the real intended rule (karaka well-placed /
angular-or-trinal from its own significations / aspecting the domain's house — not merely existing
in the chart, which is trivially always true) — re-read that doc's exact language for this before
`evaluate_witnesses()` gets written, or the "karaka" witness will silently always fire and the
whole confidence-tier system loses one of its four legs.

**Golden-chart fixture — verified against the live engine, not fabricated.** Pulled Mohan's real
chart (1975-04-22T19:15, Mysore) from a live local `/chart` call. Lagna Libra (signIndex 6).
House-by-house occupancy for the 5 v1 domains, computed directly from the live response:

| Domain | House(s) | House sign | Occupants | House lord |
|---|---|---|---|---|
| Marriage | 7 | Aries | Sun, Mercury | Mars |
| Children | 5 | Aquarius | Mars | Saturn |
| Career rise | 10 | Cancer | *(empty)* | Moon |
| Home/property | 4 | Capricorn | *(empty)* | Saturn |
| Health episode | 1, 6, 8, 12 | Libra / Pisces / Taurus / Virgo | *(empty)* / Jupiter / Venus, Ketu / *(empty)* | Venus / Jupiter / Venus / Mercury |

This is the real, verified basis for §7's own golden-chart rule ("structural assertion only... no
real marriage/kid/job dates exist... none should be fabricated").

**Synthetic fixtures — deliberately not hand-authored yet.** §7 calls for charts engineered to hit
each of §3's four qualification branches (lordship, occupation, aspect, dispositor chain) plus a
zero-witness chart. Lordship is already covered by Mohan's real chart above (Mars is both house-7
lord and, separately, a real dasha lord in his tree). Occupation and dispositor-chain need
constructed (non-real) planet-position sets — deliberately **not** authored here: `evaluate_witnesses()`/
`qualifies()` don't exist yet, so there is nothing to run a hand-picked fixture against to confirm
it actually hits the intended branch rather than a neighboring one. Authoring exact fixture
literals now would mean guessing at internal function behavior with no way to verify — the same
"trust but don't verify" mistake this session spent real effort avoiding with delegated review
output elsewhere. The aspect branch is harder-blocked: it depends on `aspects_between()`, new code
this plan itself specifies adding to `ephem.py`, which doesn't exist at all yet. **Recommendation:**
build literal fixture data in the implementation session itself, immediately after
`life_event_domains.py`/`life_event_witness.py` land, where each fixture can be authored and
verified against real running code in the same sitting — not as a disconnected prep step now.

---

## 9. Risks (carried into the MAFIP review as explicit check items)

1. **False precision** — mitigated by §5's mandatory `limits` field and §2's stability gate
   downgrade; reviewer should verify no UI path drops these fields.
2. **Sensitive domains** (health, children) — `AddObservedEventForm.tsx` already has a consent
   checkbox precedent for `relationship.marriage_registered`; life-event predictions for
   `health_episode`/`children` domains should carry the same explicit-consent framing before a
   user can resolve them, not just view them.
3. **Retrospective-vs-prospective confusion** — the single highest-stakes labelling risk (§6's
   banner text is not optional polish; it's the load-bearing honesty claim). The reviewer must
   adversarially probe every UI surface where a life-event prediction appears for language that
   could be misread as "the app predicted this before it happened."
4. **Cost** — fructification per qualified AD across 5 domains × up to 9 MDs could multiply
   request cost; §3's "qualified ADs only, confidence≥medium for PD" gates are the control; measure
   actual `/report/facts` latency against the existing 15-20s baseline (`STATUS.md` known issue #2)
   before shipping, not after.
