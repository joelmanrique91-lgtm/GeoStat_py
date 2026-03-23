# Variography Technical Backlog

> Scope: architecture and implementation-ready technical backlog (no UI polish scope).

## Architecture / foundation

### VAR-ARCH-001
- **Title:** Define variography v1 contracts package
- **Description:** Create typed request/response/entity contracts in `app/models/variography/` for compute, model, validation, publish.
- **Rationale:** Current service payloads are mostly implicit dicts; FE/BE parallelization needs stable contract boundary.
- **Dependencies:** None.
- **Risk level:** High.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Contracts exist and are importable.
  - Mandatory fields defined for request/result/validation/publish.
  - Contract version field present.

### VAR-ARCH-002
- **Title:** Define state ownership policy and dirty-flag model
- **Description:** Document and implement authoritative variography state object (`VariographySession`) with dirty flags.
- **Rationale:** Prevent stale state across Tk vars and service state.
- **Dependencies:** VAR-ARCH-001.
- **Risk level:** High.
- **Suggested owner:** Fullstack.
- **Acceptance criteria:**
  - VariographySession type defined.
  - Dirty flags (`compute_dirty`, `model_dirty`, `render_dirty`) documented and used.
  - UI-only ephemeral state explicitly separated.

### VAR-ARCH-003
- **Title:** Correct workflow readiness semantics for feature availability
- **Description:** Extend readiness contract so disabled/placeholder stages are not reported as fully ready.
- **Rationale:** Prevent misleading UX and ticket assumptions.
- **Dependencies:** None.
- **Risk level:** Medium.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Readiness response includes feature availability metadata.
  - Tests updated for domains/variography stage semantics.

## Backend / domain

### VAR-BE-001
- **Title:** Implement VariographyComputationService wrapper
- **Description:** Wrap `compute_experimental_variogram` behind typed request and response contracts.
- **Rationale:** Isolates existing primitive and enables future algorithm changes without UI breakage.
- **Dependencies:** VAR-ARCH-001.
- **Risk level:** High.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Service accepts `ExperimentalVariogramRequest`.
  - Returns `ExperimentalVariogramResult` + warnings.
  - Graceful errors for invalid params and no-pairs scenarios.

### VAR-BE-002
- **Title:** Implement VariographyValidationService issue catalog
- **Description:** Add warning/blocker codes and validation rules for compute sufficiency and model publishability.
- **Rationale:** UI needs deterministic blocker/warning propagation.
- **Dependencies:** VAR-ARCH-001.
- **Risk level:** High.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Validation returns standardized issue codes.
  - `is_valid_for_publish` computed from blockers.
  - Unit tests cover low npairs, sparse lag coverage, invalid model params.

### VAR-BE-003
- **Title:** Implement VariographyApplicationService orchestration
- **Description:** Add top-level use-cases: compute experimental, update model, validate, publish gate.
- **Rationale:** Keeps orchestration out of UI and base GeostatService.
- **Dependencies:** VAR-BE-001, VAR-BE-002.
- **Risk level:** High.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - One entry method per use-case.
  - Request context built from active analysis snapshot.
  - Structured response for UI controller.

### VAR-BE-004
- **Title:** Add computation hash caching strategy
- **Description:** Cache experimental result by hash of dataset/context/request; reuse on non-compute edits.
- **Rationale:** Avoid repeated O(n²) runs and improve responsiveness.
- **Dependencies:** VAR-BE-001.
- **Risk level:** Medium.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Hash function defined and tested.
  - Response indicates `from_cache` true/false.
  - Cache invalidates correctly on compute-dirty fields.

### VAR-BE-005
- **Title:** Implement VariographyPersistenceService skeleton
- **Description:** Add save/load methods for session fragment and publish artifact JSON v1.
- **Rationale:** Publish and reproducibility require persistence boundary.
- **Dependencies:** VAR-ARCH-001, VAR-BE-002.
- **Risk level:** Medium.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Artifact JSON emitted with version/checksum.
  - Load path validates schema version.
  - Publish blocked if blockers present.

## Frontend / UI

### VAR-FE-001
- **Title:** Create VariographyStageView module
- **Description:** Implement dedicated stage view file for controls/charts/status; remove direct placeholder-only rendering.
- **Rationale:** Prevent further growth of HomePanel monolith.
- **Dependencies:** VAR-ARCH-001.
- **Risk level:** High.
- **Suggested owner:** Frontend.
- **Acceptance criteria:**
  - New view module integrated from HomePanel variography branch.
  - No computation logic in widget callbacks.
  - Stage renders with parameter form + chart host + result status area.

### VAR-FE-002
- **Title:** Create VariographyController event mapping
- **Description:** Add controller translating UI events to application service requests and refresh intents.
- **Rationale:** Deterministic refresh rules and service decoupling.
- **Dependencies:** VAR-BE-003, VAR-FE-001.
- **Risk level:** High.
- **Suggested owner:** Fullstack.
- **Acceptance criteria:**
  - Event handlers map variable/domain/lag/direction/model/compute/publish actions.
  - Dirty-flag transitions enforced.
  - Controller receives and applies structured response DTOs.

### VAR-FE-003
- **Title:** Add Matplotlib variography renderer
- **Description:** Implement renderer for experimental points, model curve overlay, and npairs subplot.
- **Rationale:** Reuse existing plotting strategy while isolating drawing concerns.
- **Dependencies:** VAR-FE-001, VAR-ARCH-001.
- **Risk level:** Medium.
- **Suggested owner:** Frontend.
- **Acceptance criteria:**
  - Renderer consumes response DTO only.
  - Supports redraw-only path without recomputation.
  - Uses `DashboardGrid` and app theme tokens.

### VAR-FE-004
- **Title:** Integrate validation banner and publish gate UI
- **Description:** Surface warnings/blockers consistently and disable publish when blockers exist.
- **Rationale:** Prevent invalid artifacts and hidden state.
- **Dependencies:** VAR-BE-002, VAR-FE-002.
- **Risk level:** Medium.
- **Suggested owner:** Frontend.
- **Acceptance criteria:**
  - Warning/blocker list displays issue codes/messages.
  - Publish button state bound to `is_valid_for_publish`.
  - Blocked publish shows deterministic error panel.

## Integration

### VAR-INT-001
- **Title:** Wire variography stage in HomePanel with adapter boundary
- **Description:** Replace `_render_variography_view` placeholder by adapter invocation to stage view/controller.
- **Rationale:** Lowest-risk integration using existing stage router.
- **Dependencies:** VAR-FE-001, VAR-FE-002.
- **Risk level:** High.
- **Suggested owner:** Fullstack.
- **Acceptance criteria:**
  - HomePanel keeps routing responsibility only.
  - Variography-specific logic moved to dedicated modules.
  - Existing stages regression-free.

### VAR-INT-002
- **Title:** Bridge GeostatService snapshot into variography request context
- **Description:** Define adapter logic that maps analysis context snapshot/readiness to variography context fields.
- **Rationale:** Single source of truth for target/domain context.
- **Dependencies:** VAR-BE-003.
- **Risk level:** Medium.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Context mapping function tested.
  - Invalid snapshot state yields structured validation error.

### VAR-INT-003
- **Title:** Add variography activity log taxonomy
- **Description:** Emit structured events for compute/model/validate/publish lifecycle.
- **Rationale:** Traceability and debugability aligned with existing logging patterns.
- **Dependencies:** VAR-BE-003, VAR-BE-005.
- **Risk level:** Low.
- **Suggested owner:** Fullstack.
- **Acceptance criteria:**
  - Event names standardized (`variography_compute_started`, etc.).
  - Key details captured (request hash, used_points, blockers count).

## QA / testing

### VAR-QA-001
- **Title:** Contract tests for variography DTOs
- **Description:** Add tests that enforce required fields/types for compute/validate/publish contracts.
- **Rationale:** Keep FE/BE decoupled and safe for parallel development.
- **Dependencies:** VAR-ARCH-001.
- **Risk level:** High.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Failing tests on contract-breaking changes.
  - Version field compatibility checks.

### VAR-QA-002
- **Title:** Service tests for compute/validation edge cases
- **Description:** Test no-pairs, low npairs, invalid lags, non-numeric target, downsampling paths.
- **Rationale:** Variography correctness and resilience.
- **Dependencies:** VAR-BE-001, VAR-BE-002.
- **Risk level:** High.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - All critical error/warning paths covered.
  - Deterministic behavior for same seed/input.

### VAR-QA-003
- **Title:** Integration tests for stage event-to-render flow
- **Description:** Add tests for controller-driven flow: parameter edit -> compute -> render model and blockers.
- **Rationale:** Ensure refresh policy and UI orchestration are stable.
- **Dependencies:** VAR-FE-002, VAR-INT-001.
- **Risk level:** Medium.
- **Suggested owner:** Fullstack.
- **Acceptance criteria:**
  - Compute-triggering vs redraw-only events asserted.
  - Publish blocked/enabled behavior verified.

## Refactor / debt

### VAR-REF-001
- **Title:** Reduce HomePanel variography responsibility
- **Description:** Remove variography-specific widget/state logic from HomePanel after stage module handoff.
- **Rationale:** Limits future regression footprint.
- **Dependencies:** VAR-INT-001.
- **Risk level:** Medium.
- **Suggested owner:** Frontend.
- **Acceptance criteria:**
  - HomePanel variography methods become thin delegates.
  - No direct variography computation calls in HomePanel.

### VAR-REF-002
- **Title:** Add renderer interface extension for variography
- **Description:** Extend `app/ui/renderers/base.py` with a variography renderer contract.
- **Rationale:** Keep plotting architecture consistent with EDA/Spatial renderers.
- **Dependencies:** VAR-FE-003.
- **Risk level:** Low.
- **Suggested owner:** Frontend.
- **Acceptance criteria:**
  - Interface and implementation compile/import cleanly.
  - Variography rendering path uses the interface, not concrete class directly.

### VAR-REF-003
- **Title:** Performance backlog seed for O(n²) optimization
- **Description:** Create follow-up technical spike for pair search optimization (vectorization/spatial indexing).
- **Rationale:** Existing primitive may become bottleneck at scale.
- **Dependencies:** VAR-BE-001 baseline.
- **Risk level:** Medium.
- **Suggested owner:** Backend.
- **Acceptance criteria:**
  - Spike doc includes benchmark baseline and candidate optimization approaches.
  - Clear go/no-go criteria for implementation phase.

---

## Explicit design-question answers

1. **Should Variography live inside HomePanel initially, or be extracted as stage module now?**
   - Keep HomePanel as router, but extract Variography as a dedicated stage module now.

2. **How should compute_experimental_variogram be wrapped and exposed?**
   - Through `VariographyComputationService` with typed request/response and validation/caching.

3. **Minimum contract so FE/BE can work in parallel?**
   - Compute request/response + validation issue schema + publish response schema with version field.

4. **What state must stop living in Tk variables?**
   - Active compute parameters, current model structures, publish readiness/warnings/blockers.

5. **How should publish blockers and warnings propagate to UI?**
   - As standardized issue objects from ValidationService, returned by ApplicationService on every relevant action.

6. **Which parts can be reused without dangerous coupling?**
   - DashboardGrid, theme helpers, ActivityLogService, and the current variogram primitive (wrapped).

7. **Minimal viable architecture avoiding rewrite?**
   - Stage module + controller + application/domain services + DTO contracts; HomePanel remains orchestrator.

8. **Ideal target architecture after incremental refactor?**
   - Feature-based modules for all stages with consistent controller/service boundaries and unified session state management.
