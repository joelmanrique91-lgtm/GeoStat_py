# Variography Execution Sequence

## A. Critical path

1. **Freeze contracts and session state first** (`TKT-VAR-A01`, `TKT-VAR-A03`).
   - Reason: all streams rely on stable DTO and authoritative state semantics.
2. **Create context mapper and readiness semantics** (`TKT-VAR-A02`, `TKT-VAR-A04`).
   - Reason: prevents FE/BE divergence in source context.
3. **Wrap compute + validation baseline** (`TKT-VAR-B01`, `TKT-VAR-C01`).
   - Reason: provides backend core for stage integration and blocker/warning outputs.
4. **Wire stage shell + controller** (`TKT-VAR-D01`, `TKT-VAR-D02`).
   - Reason: unlocks UI integration without direct primitive calls.
5. **Deliver experimental flow rendering + deterministic refresh** (`TKT-VAR-E01`, `TKT-VAR-E02`, `TKT-VAR-E03`).
   - Reason: first usable variography slice.

---

## B. Parallel workstreams

## Backend stream
- Start after contracts frozen:
  - `TKT-VAR-B01`, `TKT-VAR-C01` (P0)
  - Then `TKT-VAR-B03`, `TKT-VAR-C02`, `TKT-VAR-C03`, `TKT-VAR-G01`
  - Optional later: `TKT-VAR-C04`, `TKT-VAR-I02`

## Frontend stream
- Start once A01/A02 are stable:
  - `TKT-VAR-D01`, `TKT-VAR-D03`
  - Then `TKT-VAR-D02`, `TKT-VAR-E01`, `TKT-VAR-E03`
  - Then modeling: `TKT-VAR-F01`, `TKT-VAR-F02`, `TKT-VAR-F03`

## Integration stream
- `TKT-VAR-E02` (controller + service refresh rules)
- `TKT-VAR-G02` (publish action wiring)
- `TKT-VAR-I01` (HomePanel responsibility reduction)

## QA stream
- Early and continuous:
  - `TKT-VAR-H01` starts right after A01.
  - `TKT-VAR-H02` starts after B01/C01.
  - `TKT-VAR-H04` starts after D01.
  - `TKT-VAR-H03` starts after D02/E02.

---

## C. Phase alignment (to `docs/VARIOGRAPHY_INTEGRATION_PLAN.md`)

### Phase 0 (stabilization prerequisites)
- `TKT-VAR-A01`, `TKT-VAR-A02`, `TKT-VAR-A03`, `TKT-VAR-A04`

### Phase 1 (backend/domain foundation)
- `TKT-VAR-B01`, `TKT-VAR-C01`, `TKT-VAR-B04`, `TKT-VAR-B03`

### Phase 2 (UI shell integration)
- `TKT-VAR-D01`, `TKT-VAR-D02`, `TKT-VAR-D03`

### Phase 3 (experimental variography workflow)
- `TKT-VAR-E01`, `TKT-VAR-E02`, `TKT-VAR-E03`, `TKT-VAR-E04`

### Phase 4 (modeling workflow)
- `TKT-VAR-C02`, `TKT-VAR-F01`, `TKT-VAR-F02`, `TKT-VAR-F03`, `TKT-VAR-C04`

### Phase 5 (publish and traceability)
- `TKT-VAR-C03`, `TKT-VAR-G01`, `TKT-VAR-G02`, `TKT-VAR-G03`

### Continuous QA/Regression
- `TKT-VAR-H01`, `TKT-VAR-H02`, `TKT-VAR-H03`, `TKT-VAR-H04`

### Stabilization tail
- `TKT-VAR-I01`, `TKT-VAR-I02`, `TKT-VAR-I03`

---

## D. Blocking dependencies

- `TKT-VAR-A01` blocks: `A02`, `A03`, `B01`, `C01`, `D01`, `H01`.
- `TKT-VAR-A02` blocks: `D02`, `B01` production usage.
- `TKT-VAR-A03` blocks: `E02`, `B03`.
- `TKT-VAR-B01` + `C01` block: `D02`, `E01`, `E03`, `H02`.
- `TKT-VAR-D01` blocks: `D02`, `E01`, `H04`.
- `TKT-VAR-D02` blocks: `E02`, `E04`, `G02`, `H03`.
- `TKT-VAR-C02` blocks: `F01`, `F02`, `F03`, `C04`.
- `TKT-VAR-C03` + `C01` block: `G01`.
- `TKT-VAR-G01` blocks: `G02`, `G03`.

---

## E. Recommended milestone slices

## Milestone 1 — Contracts + compute wrapper + validation baseline (P0)
- Tickets:
  - `A01`, `A02`, `A03`, `A04`, `B01`, `C01`, `H01`
- Outcome:
  - frozen contracts
  - wrapped compute entry point
  - first-class blockers/warnings

## Milestone 2 — Stage shell + experimental compute UX
- Tickets:
  - `D01`, `D02`, `D03`, `E01`, `E02`, `E03`, `H02`, `H04`
- Outcome:
  - usable experimental variography stage with deterministic refresh

## Milestone 3 — Modeling + model validation
- Tickets:
  - `C02`, `F01`, `F02`, `F03`, `C04`, `H03`
- Outcome:
  - modeled variography workflow with readiness indicators

## Milestone 4 — Publish + traceability + stabilization
- Tickets:
  - `C03`, `G01`, `G02`, `G03`, `I01`, `I03`
- Outcome:
  - publishable artifact and traceability complete

## Milestone 5 — Performance hardening (optional)
- Tickets:
  - `B03` (if deferred), `I02`
- Outcome:
  - scalability roadmap validated with benchmarks

---

## F. Suggested PR slicing

1. **PR-1 (Foundation contracts)**
   - `A01`, partial `A03`, `H01` skeleton.
2. **PR-2 (Context bridge + readiness semantics)**
   - `A02`, `A04`.
3. **PR-3 (Compute + validation baseline)**
   - `B01`, `C01`, `B04`, `H02` initial cases.
4. **PR-4 (Stage shell + controller skeleton)**
   - `D01`, `D03`, base `D02`.
5. **PR-5 (Experimental rendering + refresh matrix)**
   - `E01`, `E02`, `E03`, `E04`, `H03`.
6. **PR-6 (Modeling backend + UI)**
   - `C02`, `F01`, `F02`, `F03`, `C04`.
7. **PR-7 (Persistence + publish)**
   - `C03`, `G01`, `G02`, `G03`.
8. **PR-8 (Refactor and stabilization)**
   - `I01`, `H04`, `I03`.
9. **PR-9 (Performance spike)**
   - `I02`.

Guideline: keep each PR focused to one core concern and <= ~600 net LOC where feasible.

---

## Explicit answers required by planning review

1. **Which tickets can start immediately?**
   - `A01`, `A04`, `H01` (with initial schema assertions), and planning setup for `A02`.

2. **Which P0 tickets unblock the rest?**
   - `A01`, `A02`, `A03`, `A04`, `B01`, `C01`, `D01`, `D02`, `E01`, `E02`, `E03`, `G01`, `H01`, `H02`, `H04`.

3. **Which backend/frontend tickets can run in parallel after contracts are frozen?**
   - Backend: `B01`, `C01`, `B04`; Frontend: `D01`, `D03`; QA: `H01`.

4. **Which tickets should be fullstack because separation would create churn?**
   - `A02`, `D02`, `E02`, `G02`, `I03`.

5. **Minimum ticket set for first usable experimental variography slice?**
   - `A01`, `A02`, `A03`, `A04`, `B01`, `C01`, `D01`, `D02`, `D03`, `E01`, `E02`, `E03`, `H01`, `H02`, `H04`.

6. **Minimum ticket set for publishable modeled variography?**
   - Experimental slice minimum + `C02`, `C03`, `F01`, `F02`, `F03`, `G01`, `G02`, `G03`, `H03`.
