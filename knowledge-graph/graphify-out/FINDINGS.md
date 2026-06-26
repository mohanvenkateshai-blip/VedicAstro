# FINDINGS — VedicAstro Knowledge Graph

Query results and structural discoveries documented here for the GraphRAG/predict endpoint.

---

## Finding 01 — Why Rohini Bridges Business-Finance, Wedding, Scoring, and Samskara Muhurtas

**Query:** "Why does Rohini bridge Business Finance, Wedding, Scoring, and Samskara muhurtas?"
**Date:** 2026-06-25
**Graph state:** 333 nodes, 1079 links, 21 communities

### Graph Evidence

**Rohini's position:** Community 1 (Mars-ruled, adversarial/transactional cluster). Degree 32. Betweenness #1 (0.0528).

**Activities where Rohini is FAVORED (prescribed):**
| Community | Activities |
|-----------|-----------|
| Com 2 (Samskaras/Ceremonies) | Wedding, House Warming, Digging Foundation, Investing |
| Com 0 (General Muhurta) | Installing Deity, Performing Puja/Yajna, Relocation, Returning Home, Dance/Music, Buying Cattle |
| Com 4 (Construction/Growth) | Starting Construction, Sowing Seeds, Planting Trees, Purchasing Property, Wearing New Clothes |
| Com 1 (own community) | Buying & General Transactions, Engagement, Entering New House |

**Activities where Rohini is AVOIDED (contraindicated):**
| Community | Activities |
|-----------|-----------|
| Com 1 (own) | General Surgery, Oral Surgery, Laxatives, Paying Debts, Lending, Filing a Case, Resignation, Selling Property, Dividing Property, Harvesting |

### The Structural Answer

Rohini creates betweenness by living in Community 1 (the aggressive/transactional cluster) while being PRESCRIBED for activities in Communities 0, 2, and 4. This is rare — most nakshatras are prescribed for activities *within* their own community. Rohini is an exception because its Vedic nature cuts across the community partition.

**The Vedic mechanic:** Rohini is a Fixed/Sthira nakshatra (deity: Brahma, the Creator; Moon's own nakshatra). "Fixed" means: things started under Rohini are meant to *last*. This single property explains every edge:

- **Wedding (Com 2):** You want the bond to be permanent → Rohini prescribed.
- **Construction, Sowing, Planting (Com 4):** You want the structure/crop to be permanent → Rohini prescribed.
- **Investment, Buying Property, Buying Cattle (Com 2/0):** You want the wealth to be permanent → Rohini prescribed.
- **Installing Deity (Com 0):** A consecrated idol must remain forever → Rohini prescribed.
- **Puja/Yajna, Engagement (Com 1):** These begin permanent relationships → Rohini prescribed.

The contraindications are the mirror image. **Rohini is avoided for every activity that requires change, separation, or release:**
- Surgery (cutting/removal) → Fixed nakshatra inhibits the wound from healing/separating.
- Paying debts, Resignation → You want the debt/job relationship to *end* — fixedness works against you.
- Selling Property, Dividing Property, Harvesting → Separation/disposal — fixed nature opposes release.
- Filing a Case → You want resolution (movement), not stasis.

### Why It Shows as #1 Betweenness (Not Just High Degree)

Pushya has higher *degree* (43 vs. 32) but lower betweenness. The difference:

- **Pushya** is universally benefic — it's in the same community as most activities it serves. Its links stay *within* clusters.
- **Rohini** sits in the adversarial/transactional Community 1 but its prescriptions reach Communities 0, 2, and 4. Its links *cross* community boundaries repeatedly, making it a bridge node rather than a hub node.

Betweenness = fraction of shortest paths that pass through a node. Rohini is the shortest route between the aggressive/disposal cluster (Community 1) and the constructive/permanent cluster (Community 4) because both clusters have direct links to it but relatively few links to each other.

### Implication for the `/predict` Endpoint

When scoring a muhurta:
- If the activity is in the "permanence" semantic family (wedding, construction, planting, property purchase, consecration): Rohini gives +14 (Prescribed Nakshatra factor).
- If the activity is in the "separation/release" semantic family (surgery, debt, resignation, disposal, harvesting): Rohini gives -16 (Contraindicated Nakshatra factor).
- The activity's community membership in this graph is a reliable proxy for which family it belongs to.

A GraphRAG rule could be: `if nakshatra == Rohini → look up activity's community → if com in {2, 4, "construction"}: +14; if com in {1_separation}: -16`.

---
