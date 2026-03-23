# Variography Implementation Tickets

This ticket set converts approved architecture/backlog into execution-ready work items.

## EPIC A: Foundation / Contracts / State

### TKT-VAR-A01
- **Title:** Create typed variography contracts package (v1)
- **Epic:** EPIC A
- **Type:** backend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Create `app/models/variography/` with typed contracts for request/result/validation/publish/session state.
- **Scope in:** `VariographySession`, `ExperimentalVariogramRequest`, `DirectionDefinition`, `LagDefinition`, `ExperimentalVariogramResult`, `VariogramModel`, `ModelStructure`, `ModelValidationResult`, `VariographyPublishArtifact`.
- **Scope out:** algorithm implementation, UI integration.
- **Why this ticket exists:** FE/BE parallelization depends on frozen, explicit contracts.
- **Dependencies:** none.
- **Files/modules likely touched:**
  - `app/models/variography/__init__.py` (new)
  - `app/models/variography/contracts.py` (new)
  - `app/models/variography/session.py` (new)
- **Acceptance criteria:**
  1. All contracts are importable from `app.models.variography`.
  2. Contract includes `schema_version` or equivalent version field.
  3. Contract fields match `docs/VARIOGRAPHY_TARGET_ARCHITECTURE.md` section I.
- **Technical notes:** prefer `dataclass(frozen=True)` for immutable request/result DTOs.
- **Risks:** over/under-specification causing churn.
- **Definition of done:** code merged + unit contract tests green.

### TKT-VAR-A02
- **Title:** Implement variography request/response mappers and context bridge
- **Epic:** EPIC A
- **Type:** fullstack
- **Priority:** P0
- **Estimated size:** M
- **Description:** Create mapping helpers from `GeostatService.get_analysis_context_snapshot()` + UI payloads into typed variography contracts.
- **Scope in:** one canonical mapper module and validation for missing context columns.
- **Scope out:** computation execution.
- **Why this ticket exists:** avoids duplicated request-building logic across controller/service.
- **Dependencies:** TKT-VAR-A01.
- **Files/modules likely touched:**
  - `app/services/variography_context_mapper.py` (new)
  - `app/services/geostat_service.py` (read-only integration hook)
- **Acceptance criteria:**
  1. Mapper returns valid `ExperimentalVariogramRequest` from context + parameters.
  2. Invalid context returns structured validation error code.
  3. Unit tests cover missing target/domain/xyz cases.
- **Technical notes:** mapper is pure function module.
- **Risks:** duplicate context semantics with existing readiness logic.
- **Definition of done:** mapper used by app service and controller without duplicate code.

### TKT-VAR-A03
- **Title:** Add authoritative `VariographySession` state and dirty flags
- **Epic:** EPIC A
- **Type:** backend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Implement session state object and transitions for `compute_dirty`, `model_dirty`, `render_dirty`.
- **Scope in:** session lifecycle methods (init, update on parameter/model edit, clear).
- **Scope out:** persistence storage and UI rendering.
- **Why this ticket exists:** remove critical analysis state from Tk-only variables.
- **Dependencies:** TKT-VAR-A01.
- **Files/modules likely touched:**
  - `app/models/variography/session.py`
  - `app/services/variography_application_service.py` (new)
- **Acceptance criteria:**
  1. Dirty flag transitions documented in code and tests.
  2. Session captures last accepted request/result/model/validation.
  3. No direct mutation of compute-critical state in UI tests.
- **Technical notes:** expose read-only snapshot method.
- **Risks:** stale state if transitions incomplete.
- **Definition of done:** service tests prove deterministic flag transitions.

### TKT-VAR-A04
- **Title:** Correct workflow readiness semantics for variography availability
- **Epic:** EPIC A
- **Type:** backend
- **Priority:** P0
- **Estimated size:** S
- **Description:** Extend readiness payload to express feature availability separately from data readiness.
- **Scope in:** add `feature_enabled`/equivalent metadata for `variography` stage.
- **Scope out:** full domains redesign.
- **Why this ticket exists:** current readiness can be misread as “fully implemented”.
- **Dependencies:** none.
- **Files/modules likely touched:**
  - `app/services/geostat_service.py`
  - `tests/test_workflow_state.py`
- **Acceptance criteria:**
  1. `get_workflow_readiness()` includes availability metadata for variography.
  2. Existing workflow tests updated and passing.
  3. No regressions in Datos/EDA/Cutoffs/Espacial readiness semantics.
- **Technical notes:** maintain backward compatibility fields where possible.
- **Risks:** downstream UI assumptions break.
- **Definition of done:** readiness contract and tests stabilized.

---

## EPIC B: Backend Computation

### TKT-VAR-B01
- **Title:** Implement `VariographyComputationService` wrapper over experimental primitive
- **Epic:** EPIC B
- **Type:** backend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Wrap `compute_experimental_variogram` from `app/services/visualization_service.py` with typed inputs/outputs.
- **Scope in:** conversion to/from DTOs, structured error handling.
- **Scope out:** model fitting.
- **Why this ticket exists:** enforce “wrapped, not ad hoc” compute access.
- **Dependencies:** TKT-VAR-A01, TKT-VAR-A02.
- **Files/modules likely touched:**
  - `app/services/variography_computation_service.py` (new)
  - `app/services/visualization_service.py` (optional adapter helper)
- **Acceptance criteria:**
  1. Service accepts `ExperimentalVariogramRequest` and returns `ExperimentalVariogramResult`.
  2. Error conditions map to typed validation/error codes.
  3. Unit tests cover no-pairs and invalid lag params.
- **Technical notes:** keep primitive logic untouched in first pass.
- **Risks:** hidden assumptions in primitive inputs.
- **Definition of done:** wrapper used by app service only.

### TKT-VAR-B02
- **Title:** Add directional filtering support contract path (pre-compute)
- **Epic:** EPIC B
- **Type:** backend
- **Priority:** P1
- **Estimated size:** L
- **Description:** Implement directional request handling (omnidirectional pass-through first; directional filter path optional behind flag).
- **Scope in:** directional parameter validation and hook points.
- **Scope out:** full anisotropic variogram algorithm rewrite.
- **Why this ticket exists:** contract requires direction fields; computation path must honor or explicitly reject unsupported combinations.
- **Dependencies:** TKT-VAR-B01.
- **Files/modules likely touched:**
  - `app/services/variography_computation_service.py`
  - `app/services/variography_validation_service.py`
- **Acceptance criteria:**
  1. Omnidirectional mode supported end-to-end.
  2. Directional unsupported modes return deterministic blocker/warning code.
  3. Tests validate mode behavior matrix.
- **Technical notes:** use feature flag if needed.
- **Risks:** partial directional semantics confusing users.
- **Definition of done:** explicit and test-backed directional behavior.

### TKT-VAR-B03
- **Title:** Implement computation hash caching
- **Epic:** EPIC B
- **Type:** backend
- **Priority:** P1
- **Estimated size:** M
- **Description:** Cache experimental results by hash(dataset signature + context + request).
- **Scope in:** hash generation, cache read/write, invalidation rules.
- **Scope out:** cross-session cache persistence.
- **Why this ticket exists:** control O(n²) compute cost and enforce deterministic reuse policy.
- **Dependencies:** TKT-VAR-B01, TKT-VAR-A03.
- **Files/modules likely touched:**
  - `app/services/variography_application_service.py`
  - `app/services/variography_cache.py` (new)
- **Acceptance criteria:**
  1. Repeat compute with identical hash returns `from_cache=true`.
  2. Any compute-dirty field change invalidates cache.
  3. Cache behavior covered by service tests.
- **Technical notes:** in-memory cache in phase 1.
- **Risks:** stale cache due to incomplete hash fields.
- **Definition of done:** stable hash + tested invalidation matrix.

### TKT-VAR-B04
- **Title:** Add compute lifecycle activity logging
- **Epic:** EPIC B
- **Type:** backend
- **Priority:** P1
- **Estimated size:** S
- **Description:** Emit `variography_compute_started/succeeded/failed` events with request hash, used points, warnings count.
- **Scope in:** structured details payload in `ActivityLogService` usage.
- **Scope out:** export UI.
- **Why this ticket exists:** traceability and operational debugging.
- **Dependencies:** TKT-VAR-B01.
- **Files/modules likely touched:**
  - `app/services/variography_application_service.py`
  - `app/services/activity_log_service.py` (usage only)
- **Acceptance criteria:**
  1. Events emitted for success/failure paths.
  2. Logs contain request hash and point counts.
  3. Logging tests assert event names and core details.
- **Technical notes:** reuse existing JSONL schema.
- **Risks:** noisy logs if over-emitted.
- **Definition of done:** event taxonomy documented + tested.

---

## EPIC C: Backend Validation / Persistence

### TKT-VAR-C01
- **Title:** Implement `VariographyValidationService` issue catalog
- **Epic:** EPIC C
- **Type:** backend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Create warning/blocker code system and validation rules for request/result/model/publishability.
- **Scope in:** issue object schema (`code`, `message`, `severity`, `path`).
- **Scope out:** UI formatting.
- **Why this ticket exists:** blockers must be first-class outputs and deterministic.
- **Dependencies:** TKT-VAR-A01, TKT-VAR-B01.
- **Files/modules likely touched:**
  - `app/services/variography_validation_service.py` (new)
  - `app/models/variography/contracts.py`
- **Acceptance criteria:**
  1. Validation returns structured blockers/warnings.
  2. `is_valid_for_publish` derived only from blocker set.
  3. Tests cover low npairs, sparse lag coverage, invalid model params.
- **Technical notes:** centralize issue codes in one module.
- **Risks:** rule churn after UI integration.
- **Definition of done:** issue codes stable and documented.

### TKT-VAR-C02
- **Title:** Implement `VariographyModelService` core model operations
- **Epic:** EPIC C
- **Type:** backend
- **Priority:** P1
- **Estimated size:** L
- **Description:** Add model structure CRUD, theoretical curve generation, and fit metric calculation hooks.
- **Scope in:** nugget + structures list + evaluation scaffolding.
- **Scope out:** advanced auto-fit algorithms (beyond agreed minimal).
- **Why this ticket exists:** modeling UX depends on backend model semantics.
- **Dependencies:** TKT-VAR-A01, TKT-VAR-C01.
- **Files/modules likely touched:**
  - `app/services/variography_model_service.py` (new)
- **Acceptance criteria:**
  1. Service can add/remove/update structures deterministically.
  2. Service returns model curve samples compatible with renderer contract.
  3. Validation integration reports publish blockers for invalid structures.
- **Technical notes:** keep fit method pluggable.
- **Risks:** numerical stability and parameter bounds.
- **Definition of done:** model operations + tests green.

### TKT-VAR-C03
- **Title:** Implement `VariographyPersistenceService` artifact v1
- **Epic:** EPIC C
- **Type:** backend
- **Priority:** P1
- **Estimated size:** M
- **Description:** Save/load session fragment and publish artifact JSON with version and checksum.
- **Scope in:** filesystem persistence under project paths, schema version checks.
- **Scope out:** remote storage.
- **Why this ticket exists:** publish path requires durable artifact contract.
- **Dependencies:** TKT-VAR-A01, TKT-VAR-C01.
- **Files/modules likely touched:**
  - `app/services/variography_persistence_service.py` (new)
  - `app/utils/paths.py` (if new directory constants needed)
- **Acceptance criteria:**
  1. Publish artifact writes valid JSON v1.
  2. Load validates version and checksum.
  3. Publish fails with blocker code when validation fails.
- **Technical notes:** include UTC timestamps and context snapshot.
- **Risks:** schema evolution management.
- **Definition of done:** persistence tests pass and artifact examples documented.

### TKT-VAR-C04
- **Title:** Add PSD validation hook for modeled covariance compatibility
- **Epic:** EPIC C
- **Type:** backend
- **Priority:** P2
- **Estimated size:** M
- **Description:** Add optional positive semi-definite sanity checks for model configuration.
- **Scope in:** validation hook and blocker/warning issuance.
- **Scope out:** exhaustive geostatistical proofing engine.
- **Why this ticket exists:** requested must-have test matrix includes PSD validation.
- **Dependencies:** TKT-VAR-C02, TKT-VAR-C01.
- **Files/modules likely touched:**
  - `app/services/variography_validation_service.py`
- **Acceptance criteria:**
  1. PSD check callable from publish validation flow.
  2. Failure yields standardized blocker code.
  3. Unit tests include pass/fail PSD scenarios.
- **Technical notes:** allow feature toggle if expensive.
- **Risks:** false positives/negatives.
- **Definition of done:** check integrated and tested.

---

## EPIC D: Frontend Stage Shell / Layout

### TKT-VAR-D01
- **Title:** Create `VariographyStageView` module and wire HomePanel router
- **Epic:** EPIC D
- **Type:** frontend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Create dedicated stage module and replace `_render_variography_view` placeholder with delegated render call.
- **Scope in:** stage container, parameter form shell, result panel shell.
- **Scope out:** final experimental compute UX logic.
- **Why this ticket exists:** approved architecture requires dedicated stage module now.
- **Dependencies:** TKT-VAR-A01.
- **Files/modules likely touched:**
  - `app/ui/panels/stages/variography_stage_view.py` (new)
  - `app/ui/panels/home_panel.py`
- **Acceptance criteria:**
  1. HomePanel no longer renders static placeholder for variography.
  2. Stage view initializes with typed default state contract.
  3. Existing stages still render unchanged.
- **Technical notes:** keep HomePanel as router only.
- **Risks:** regression in stage switching.
- **Definition of done:** UI smoke tests and workflow switch tests pass.

### TKT-VAR-D02
- **Title:** Add `VariographyController` and bind UI events
- **Epic:** EPIC D
- **Type:** fullstack
- **Priority:** P0
- **Estimated size:** M
- **Description:** Introduce controller layer between stage view and application service with deterministic event mapping.
- **Scope in:** event handlers for parameter edit/compute/model edit/publish.
- **Scope out:** advanced UI polishing.
- **Why this ticket exists:** remove direct service calls from widgets and enforce refresh contract.
- **Dependencies:** TKT-VAR-A02, TKT-VAR-A03, TKT-VAR-D01.
- **Files/modules likely touched:**
  - `app/ui/controllers/variography_controller.py` (new)
  - `app/ui/panels/stages/variography_stage_view.py`
- **Acceptance criteria:**
  1. All variography actions routed through controller.
  2. Controller emits action result object consumed by view.
  3. No direct call to `compute_experimental_variogram` anywhere in UI modules.
- **Technical notes:** controller owns refresh decision matrix.
- **Risks:** duplicated logic across view/controller if boundaries unclear.
- **Definition of done:** controller contract tests + UI wiring tests green.

### TKT-VAR-D03
- **Title:** Extend renderer base with Variography interface
- **Epic:** EPIC D
- **Type:** frontend
- **Priority:** P1
- **Estimated size:** S
- **Description:** Add variography renderer abstraction to `app/ui/renderers/base.py` and export in renderer package.
- **Scope in:** interface + context dataclass.
- **Scope out:** concrete plotting details.
- **Why this ticket exists:** keep plotting architecture consistent with EDA/Spatial patterns.
- **Dependencies:** TKT-VAR-D01.
- **Files/modules likely touched:**
  - `app/ui/renderers/base.py`
  - `app/ui/renderers/__init__.py`
- **Acceptance criteria:**
  1. New abstract renderer interface compiles/imports.
  2. Stage view depends on interface, not concrete class.
  3. Existing renderer tests continue passing.
- **Technical notes:** avoid breaking current imports.
- **Risks:** import cycles.
- **Definition of done:** interface wired and non-breaking.

---

## EPIC E: Frontend Experimental Variography UX

### TKT-VAR-E01
- **Title:** Implement `MatplotlibVariographyRenderer` (experimental + npairs)
- **Epic:** EPIC E
- **Type:** frontend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Create renderer for experimental points/curve and npairs subplot using `DashboardGrid`.
- **Scope in:** chart rendering from typed response DTO.
- **Scope out:** modeling overlay edits.
- **Why this ticket exists:** first usable experimental slice requires visualization.
- **Dependencies:** TKT-VAR-D03, TKT-VAR-B01.
- **Files/modules likely touched:**
  - `app/ui/renderers/mpl_variography_renderer.py` (new)
  - `app/ui/panels/dashboard_grid.py` (reuse)
- **Acceptance criteria:**
  1. Renderer draws lag-gamma scatter/line and npairs chart.
  2. Supports redraw-only without recompute call.
  3. Handles empty/blocked result gracefully with message panel.
- **Technical notes:** keep style tokens from `app/ui/theme.py`.
- **Risks:** chart readability for sparse data.
- **Definition of done:** visual render tests and no exceptions on edge payloads.

### TKT-VAR-E02
- **Title:** Implement parameter edit -> dirty flag -> refresh behavior
- **Epic:** EPIC E
- **Type:** fullstack
- **Priority:** P0
- **Estimated size:** M
- **Description:** Connect lag/direction/target/domain edits to deterministic refresh rules in controller/session.
- **Scope in:** full recompute vs redraw-only vs validation-only mapping.
- **Scope out:** auto-optimization heuristics.
- **Why this ticket exists:** approved architecture requires deterministic refresh semantics.
- **Dependencies:** TKT-VAR-A03, TKT-VAR-D02, TKT-VAR-B03.
- **Files/modules likely touched:**
  - `app/ui/controllers/variography_controller.py`
  - `app/services/variography_application_service.py`
- **Acceptance criteria:**
  1. Compute-dirty events trigger compute path.
  2. Model-only edits trigger redraw/validation without recompute.
  3. Tests assert event-to-action matrix.
- **Technical notes:** matrix documented in code comments.
- **Risks:** accidental recompute storms.
- **Definition of done:** deterministic event matrix verified by tests.

### TKT-VAR-E03
- **Title:** Render warnings/blockers banner for experimental stage
- **Epic:** EPIC E
- **Type:** frontend
- **Priority:** P0
- **Estimated size:** S
- **Description:** Display validation warnings and blockers from response DTO in dedicated status area.
- **Scope in:** issue list rendering and severity styling.
- **Scope out:** localization.
- **Why this ticket exists:** blockers/warnings are first-class outputs.
- **Dependencies:** TKT-VAR-C01, TKT-VAR-D01.
- **Files/modules likely touched:**
  - `app/ui/panels/stages/variography_stage_view.py`
- **Acceptance criteria:**
  1. Warning and blocker lists render with issue codes.
  2. Empty state when no issues.
  3. Snapshot tests validate rendering behavior.
- **Technical notes:** avoid embedding validation logic in UI.
- **Risks:** inconsistent issue formatting.
- **Definition of done:** UI behavior tests pass for warning/blocker scenarios.

### TKT-VAR-E04
- **Title:** Add “Compute” action and loading/error UX state machine
- **Epic:** EPIC E
- **Type:** frontend
- **Priority:** P1
- **Estimated size:** S
- **Description:** Add explicit compute trigger with loading, success, error, and cached states.
- **Scope in:** button states and progress messaging.
- **Scope out:** async job queue.
- **Why this ticket exists:** predictable operator workflow and clear feedback.
- **Dependencies:** TKT-VAR-D02, TKT-VAR-B01.
- **Files/modules likely touched:**
  - `app/ui/panels/stages/variography_stage_view.py`
  - `app/ui/controllers/variography_controller.py`
- **Acceptance criteria:**
  1. Compute button disabled during in-flight compute.
  2. Error path shows structured message from response.
  3. Cached run shows “from cache” indicator.
- **Technical notes:** synchronous compute can still show transient state.
- **Risks:** UI freezing on long compute.
- **Definition of done:** compute UX states verified by UI tests.

---

## EPIC F: Frontend Modeling UX

### TKT-VAR-F01
- **Title:** Implement model structures table (nugget + nested structures)
- **Epic:** EPIC F
- **Type:** frontend
- **Priority:** P1
- **Estimated size:** M
- **Description:** Add table editor for model structures with add/remove/edit actions.
- **Scope in:** form controls and client-side field validation hints.
- **Scope out:** full spreadsheet UX.
- **Why this ticket exists:** modeling workflow requires structure editing.
- **Dependencies:** TKT-VAR-C02, TKT-VAR-D01.
- **Files/modules likely touched:**
  - `app/ui/panels/stages/variography_stage_view.py`
  - `app/ui/controllers/variography_controller.py`
- **Acceptance criteria:**
  1. User can add/remove/update structures.
  2. Invalid edits produce validation issue from backend, not silent failure.
  3. Model edits set `model_dirty=true` and do not force recompute.
- **Technical notes:** index structures by stable row id.
- **Risks:** data entry error handling complexity.
- **Definition of done:** behavior tests for structure CRUD and dirty flags.

### TKT-VAR-F02
- **Title:** Overlay model curve on experimental plot
- **Epic:** EPIC F
- **Type:** frontend
- **Priority:** P1
- **Estimated size:** M
- **Description:** Extend variography renderer to draw theoretical model curve(s) over experimental data.
- **Scope in:** line rendering + legend + fit score display.
- **Scope out:** advanced styling/polish.
- **Why this ticket exists:** model interpretation requires side-by-side visual comparison.
- **Dependencies:** TKT-VAR-E01, TKT-VAR-C02.
- **Files/modules likely touched:**
  - `app/ui/renderers/mpl_variography_renderer.py`
- **Acceptance criteria:**
  1. Curve overlay visible when model exists.
  2. No overlay when model absent.
  3. Legend and fit score reflect current model state.
- **Technical notes:** curve samples provided by backend model service.
- **Risks:** mismatch between curve domain and lag bins.
- **Definition of done:** rendering tests for overlay/no-overlay states.

### TKT-VAR-F03
- **Title:** Model validation panel and publish readiness indicator
- **Epic:** EPIC F
- **Type:** frontend
- **Priority:** P1
- **Estimated size:** S
- **Description:** Render model-specific warnings/blockers and a clear readiness indicator.
- **Scope in:** panel showing `is_valid_for_publish` and issue lists.
- **Scope out:** recommendation engine.
- **Why this ticket exists:** modeling phase must expose publish blockers clearly.
- **Dependencies:** TKT-VAR-C01, TKT-VAR-F01.
- **Files/modules likely touched:**
  - `app/ui/panels/stages/variography_stage_view.py`
- **Acceptance criteria:**
  1. Readiness indicator updates after model edits.
  2. Blockers render with codes and linked field path.
  3. Publish button state reflects readiness.
- **Technical notes:** consume validation DTO directly.
- **Risks:** stale readiness if not refreshed after edits.
- **Definition of done:** UI tests prove readiness transitions.

---

## EPIC G: Publish / Traceability

### TKT-VAR-G01
- **Title:** Implement publish use-case in `VariographyApplicationService`
- **Epic:** EPIC G
- **Type:** backend
- **Priority:** P0
- **Estimated size:** M
- **Description:** Add publish orchestration: validate -> persist artifact -> return publish response.
- **Scope in:** hard gate on blockers, success path artifact metadata.
- **Scope out:** external registry integration.
- **Why this ticket exists:** required for publishable modeled variography slice.
- **Dependencies:** TKT-VAR-C01, TKT-VAR-C03.
- **Files/modules likely touched:**
  - `app/services/variography_application_service.py`
  - `app/services/variography_persistence_service.py`
- **Acceptance criteria:**
  1. Publish blocked when blockers exist.
  2. Successful publish returns artifact path/version/checksum.
  3. Publish response DTO consumed by controller/UI.
- **Technical notes:** ensure idempotent publish behavior when same model unchanged.
- **Risks:** partial writes.
- **Definition of done:** publish service tests pass.

### TKT-VAR-G02
- **Title:** Add publish action wiring in stage controller/view
- **Epic:** EPIC G
- **Type:** fullstack
- **Priority:** P1
- **Estimated size:** S
- **Description:** Add publish button action through controller to application service and display result state.
- **Scope in:** action invocation + success/error/blocked messaging.
- **Scope out:** export dialogs beyond local path.
- **Why this ticket exists:** expose publish functionality end-to-end.
- **Dependencies:** TKT-VAR-G01, TKT-VAR-D02.
- **Files/modules likely touched:**
  - `app/ui/controllers/variography_controller.py`
  - `app/ui/panels/stages/variography_stage_view.py`
- **Acceptance criteria:**
  1. Publish action disabled when blockers present.
  2. Success state shows artifact path/version.
  3. Blocked state lists blockers without crashing UI.
- **Technical notes:** keep side-effects in controller/service.
- **Risks:** duplicate validation calls causing inconsistent messages.
- **Definition of done:** integration tests pass publish states.

### TKT-VAR-G03
- **Title:** Extend activity log taxonomy for model + publish lifecycle
- **Epic:** EPIC G
- **Type:** backend
- **Priority:** P1
- **Estimated size:** S
- **Description:** Emit standardized events for model updates, validation outcomes, publish attempts/results.
- **Scope in:** event naming and payload schema.
- **Scope out:** analytics pipeline.
- **Why this ticket exists:** traceability requirement in approved plan.
- **Dependencies:** TKT-VAR-C01, TKT-VAR-G01.
- **Files/modules likely touched:**
  - `app/services/variography_application_service.py`
- **Acceptance criteria:**
  1. Events emitted for update_model, validate_model, publish_attempt, publish_blocked, publish_succeeded.
  2. Payload includes model hash/version and blocker counts.
  3. Activity log tests validate emitted events.
- **Technical notes:** follow existing `ActivityLogService` patterns.
- **Risks:** event naming drift.
- **Definition of done:** log taxonomy documented in code comments and tests.

---

## EPIC H: QA / Testing / Regression

### TKT-VAR-H01
- **Title:** Contract compatibility test suite (UI/service DTO)
- **Epic:** EPIC H
- **Type:** qa
- **Priority:** P0
- **Estimated size:** M
- **Description:** Build tests validating DTO compatibility and required field presence across controller/application-service boundary.
- **Scope in:** schema snapshots and backward compatibility checks.
- **Scope out:** performance benchmarking.
- **Why this ticket exists:** contract drift is highest integration risk.
- **Dependencies:** TKT-VAR-A01, TKT-VAR-D02.
- **Files/modules likely touched:**
  - `tests/test_variography_contracts.py` (new)
- **Acceptance criteria:**
  1. Missing required DTO fields fail tests.
  2. Version mismatch handling tested.
  3. Contract tests run in CI.
- **Technical notes:** snapshot tests acceptable if deterministic.
- **Risks:** brittle tests if schema changes often.
- **Definition of done:** contract suite green and required in merge gate.

### TKT-VAR-H02
- **Title:** Backend service matrix tests for compute/validate/cache/publish
- **Epic:** EPIC H
- **Type:** qa
- **Priority:** P0
- **Estimated size:** L
- **Description:** Add service-level matrix covering request validation, lag/direction handling, warnings/blockers, cache behavior, publish gating, PSD hook.
- **Scope in:** comprehensive backend matrix for variography modules.
- **Scope out:** UI rendering details.
- **Why this ticket exists:** assures backend correctness and reliability before broad UI integration.
- **Dependencies:** TKT-VAR-B01, TKT-VAR-B03, TKT-VAR-C01, TKT-VAR-G01.
- **Files/modules likely touched:**
  - `tests/test_variography_services.py` (new)
- **Acceptance criteria:**
  1. Matrix scenarios documented and automated.
  2. All blocker/warning codes tested at least once.
  3. Cache hit/miss logic and publish block logic covered.
- **Technical notes:** use small synthetic datasets.
- **Risks:** long test runtime.
- **Definition of done:** matrix suite stable and passing.

### TKT-VAR-H03
- **Title:** Frontend/controller behavior tests for deterministic refresh
- **Epic:** EPIC H
- **Type:** qa
- **Priority:** P1
- **Estimated size:** M
- **Description:** Test stage initialization, parameter edits, compute actions, dirty flags, redraw-only vs recompute decisions, warnings/blockers rendering.
- **Scope in:** behavior tests for controller/view contract.
- **Scope out:** pixel-perfect UI tests.
- **Why this ticket exists:** protects deterministic refresh model and non-regression.
- **Dependencies:** TKT-VAR-D02, TKT-VAR-E02, TKT-VAR-E03.
- **Files/modules likely touched:**
  - `tests/test_variography_ui_behavior.py` (new)
- **Acceptance criteria:**
  1. Event-to-refresh matrix assertions exist.
  2. Dirty flag transitions reflected in UI state model.
  3. Blocker rendering and publish disabled state tested.
- **Technical notes:** mock renderer and app service outputs.
- **Risks:** test fragility if UI internals change.
- **Definition of done:** behavior suite green.

### TKT-VAR-H04
- **Title:** Cross-tab regression suite (Datos/EDA/Cutoffs/Espacial)
- **Epic:** EPIC H
- **Type:** qa
- **Priority:** P0
- **Estimated size:** M
- **Description:** Add regression tests ensuring variography integration does not break existing workflow tabs.
- **Scope in:** stage switching, existing service flows, readiness and rendering pathways.
- **Scope out:** new feature behavior.
- **Why this ticket exists:** low-regression risk objective.
- **Dependencies:** TKT-VAR-D01.
- **Files/modules likely touched:**
  - `tests/test_workflow_state.py`
  - `tests/test_visual_preparation.py`
  - `tests/test_ui_render_hardening.py`
  - `tests/test_ui_geometry_manager.py`
- **Acceptance criteria:**
  1. Existing stage tests remain green with variography module present.
  2. No regressions in current readiness contracts unless explicitly updated.
  3. CI includes regression subset as required gate.
- **Technical notes:** keep previous assertions unless architecture-approved changes.
- **Risks:** hidden coupling in HomePanel.
- **Definition of done:** regression gate enforced.

---

## EPIC I: Refactor / Stabilization

### TKT-VAR-I01
- **Title:** Reduce HomePanel variography-specific responsibilities
- **Epic:** EPIC I
- **Type:** refactor
- **Priority:** P1
- **Estimated size:** M
- **Description:** Move remaining variography-specific state/callback code from HomePanel into stage module/controller.
- **Scope in:** delegate methods and remove dead placeholder code.
- **Scope out:** full decomposition of other stages.
- **Why this ticket exists:** prevent future coupling debt and align approved architecture.
- **Dependencies:** TKT-VAR-D01, TKT-VAR-D02, TKT-VAR-G02.
- **Files/modules likely touched:**
  - `app/ui/panels/home_panel.py`
  - `app/ui/panels/stages/variography_stage_view.py`
  - `app/ui/controllers/variography_controller.py`
- **Acceptance criteria:**
  1. HomePanel keeps routing + stage host responsibilities only for variography stage.
  2. Variography state variables no longer stored primarily in HomePanel Tk vars.
  3. Existing UI behavior unchanged for other stages.
- **Technical notes:** preserve function signatures used by tests where necessary.
- **Risks:** breaking AST-based regression tests.
- **Definition of done:** refactor tests and regressions pass.

### TKT-VAR-I02
- **Title:** Performance hardening spike for O(n²) experimental computation
- **Epic:** EPIC I
- **Type:** backend
- **Priority:** P2
- **Estimated size:** M
- **Description:** Benchmark current wrapped computation and propose optimization path (vectorization/spatial indexing/chunking).
- **Scope in:** benchmark harness and recommendation doc.
- **Scope out:** full optimization implementation.
- **Why this ticket exists:** preempt scale risk while keeping MVP timeline.
- **Dependencies:** TKT-VAR-B01.
- **Files/modules likely touched:**
  - `tests/bench_variography_compute.py` (new)
  - `docs/` benchmark report
- **Acceptance criteria:**
  1. Baseline timings published for representative sample sizes.
  2. Optimization options compared with complexity trade-offs.
  3. Follow-up implementation ticket recommendation generated.
- **Technical notes:** use synthetic datasets and fixed seeds.
- **Risks:** misleading benchmarks if datasets non-representative.
- **Definition of done:** benchmark artifact committed and reviewed.

### TKT-VAR-I03
- **Title:** Documentation synchronization and developer runbook
- **Epic:** EPIC I
- **Type:** fullstack
- **Priority:** P2
- **Estimated size:** S
- **Description:** Update docs with implemented contracts, issue-code catalog, and daily dev workflow for FE/BE/QA streams.
- **Scope in:** update variography docs after implementation milestones.
- **Scope out:** product-level user manual.
- **Why this ticket exists:** keep architecture and implementation in sync to reduce onboarding friction.
- **Dependencies:** TKT-VAR-A01, TKT-VAR-C01, TKT-VAR-D02.
- **Files/modules likely touched:**
  - `docs/VARIOGRAPHY_TARGET_ARCHITECTURE.md` (append implementation status section)
  - `docs/VARIOGRAPHY_IMPLEMENTATION_TICKETS.md`
- **Acceptance criteria:**
  1. Docs reflect actual code module names/paths.
  2. Runbook lists must-run local checks by role.
  3. Issue-code catalog included.
- **Technical notes:** keep scope technical (non-UX-polish).
- **Risks:** doc drift over time.
- **Definition of done:** docs reviewed by FE, BE, QA leads.

---

## Minimum ticket sets

### Minimum set for first usable **experimental variography slice**
- TKT-VAR-A01, A02, A03, A04
- TKT-VAR-B01
- TKT-VAR-C01
- TKT-VAR-D01, D02, D03
- TKT-VAR-E01, E02, E03
- TKT-VAR-H01, H02, H04

### Minimum set for **publishable modeled variography**
All experimental slice tickets +
- TKT-VAR-C02, C03
- TKT-VAR-F01, F02, F03
- TKT-VAR-G01, G02, G03
- TKT-VAR-H03
