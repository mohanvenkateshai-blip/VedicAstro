# Offline Research Workbench

## Purpose and boundary

The Research Workbench turns approved books, papers, datasets, and institutional
web sources into reviewable Vedic-rule proposals. It is deliberately outside
the live prediction path. It cannot call the prediction server, write the
knowledge graph, publish a rule pack, change a score, or generate a user-facing
forecast.

Open Deep Research, STORM, or GPT Researcher may later be connected through the
`ResearchRetriever` and `ResearchProvider` protocols. They are not dependencies
and their generated reports are never treated as evidence. Their role is to
help locate sources, propose questions, and expose disagreements; authoritative
support must remain a cited human-authored source or dataset.

## Controlled flow

1. Register a `SourceManifest` with a stable URI or local path, source tier,
   author or organisation, declared rights, publication/access dates, content
   checksum, and quote limit.
2. Apply a `SourceAllowlist`. Unknown rights, an unapproved license, a path
   outside configured roots, or an unapproved URI fails closed.
3. Retrieve immutable source content and verify its SHA-256 checksum.
4. Record extracted claims with exact citations and bounded quotes. The quote
   must exist in the checksummed content. Missing citations, missing sources,
   self-reference, circular derived claims, and LLM-report citations fail.
5. Record contradictions explicitly rather than silently selecting the most
   convenient interpretation.
6. Seal the query, documents, citations, claims, and contradictions into an
   immutable `ResearchSnapshot` checksum.
7. Draft a `RuleProposal`. Approval requires a named human Jyotisha reviewer,
   documented qualification or lineage, source-backed claims and citations,
   and at least one regression test case. Rejection is terminal and records a
   reason.
8. Export only an approved `RuleEvidenceCandidate`. This staging object aligns
   with the semantic fields of `forecasting.contracts.RuleEvidence`, but lacks
   runtime calculation provenance by design. A separate governed rule-pack
   release must add provenance and integrate it.

## Evidence and copyright safeguards

- The manifest controls the maximum quote length, capped in code at 25 words.
- Discovery-only or AI-generated material can guide queries but cannot become
  evidence for an exported rule.
- A generated synthesis is not made authoritative merely because it contains
  citations. Each selected citation must resolve to an eligible immutable
  source in the same snapshot.
- Research outputs remain proposals. Frequency of repetition across texts or
  agents is not empirical validation and must not become forecast probability.

## Evaluation

The deterministic evaluation helper reports:

- citation coverage: fraction of claims whose citation identifiers resolve;
- unsupported-claim rate: complement of citation coverage;
- contradiction coverage: fraction of supported claims represented in the
  supplied contradiction analysis.

These metrics assess research hygiene, not predictive accuracy. Predictive
value must be established separately through the outcome ledger, time-split
evaluation, calibration, and shadow releases described in `STRATEGY.md`.

## Adapter contract

Future framework adapters must implement the narrow protocols in
`cvce/research_workbench/protocols.py`. Network access, credentials, retries,
and framework-specific state belong in adapter packages, not the workbench
core. The included `LocalManifestRetriever` and
`DeterministicResearchProvider` are network-free references for development and
tests.

No adapter is authorised to bypass the allowlist, reseal modified content under
an old checksum, approve its own proposal, or write production runtime state.
