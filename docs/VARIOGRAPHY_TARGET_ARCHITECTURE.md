# Variography Target Architecture

## A. Executive Architecture Decision

### Decision
Adopt an **incremental layered feature architecture** for Variography inside the current desktop app:
- Keep current shell (`MainWindow` + `HomePanel`) for immediate integration safety.
- Extract Variography logic into dedicated modules (presentation + application + domain + persistence contracts).
- Keep HomePanel as stage orchestrator only for the first implementation wave.

### Fit with current app
This fits the existing flow where stage routing is already centralized in `HomePanel` (`_show_stage_view`, `_render_variography_view`) and computational helpers are already separated in service modules (`app/services/visualization_service.py`).

### Why lowest risk
- Avoids a full UI rewrite while reducing new coupling.
- Reuses current stage navigation and chart container (`DashboardGrid`).
- Creates explicit contracts so backend/frontend can work in parallel before deeper refactors.

---

## B. Design Principles

1. **Strict separation of concerns**
   - Tk widgets: collect/display state only.
   - Presentation/controller: map UI events to application requests.
   - Application service: orchestration and business flow.
   - Domain services: variogram/model math and validation rules.

2. **Explicit contracts first**
   - All UI-to-service calls use typed request/response contracts.
   - No new ad hoc dictionaries for variography operations.

3. **Immutable analysis input snapshots**
   - Compute inputs are captured in immutable request objects.
   - Running computation cannot mutate UI-owned fields.

4. **Single source of truth per scope**
   - Workflow/global context from `GeostatService.get_analysis_context_snapshot()`.
   - Variography analysis session state owned by a dedicated state object, not Tk vars.

5. **Deterministic refresh policy**
   - Refresh behavior driven by event type and dirty flags (compute vs redraw vs validate-only).

6. **Publishability and versioning**
   - Published variography artifacts include version metadata, context snapshot, and validation status.

---

## C. Proposed Module Boundaries

## UI Layer (Tk widgets only)
- `app/ui/panels/stages/variography_stage_view.py` (new)
  - Builds controls, tables, charts, status ribbons.
  - Emits event payloads to controller.
- `app/ui/renderers/mpl_variography_renderer.py` (new)
  - Draws experimental variograms, npairs, model curves.

## Presentation/Controller Layer
- `app/ui/controllers/variography_controller.py` (new)
  - Receives UI events.
  - Builds requests from UI + current snapshot.
  - Calls application service and updates view model.

## Application Service Layer
- `app/services/variography_application_service.py` (new)
  - Entry point for all variography use-cases:
    - preview compute
    - model fit/validate
    - publish/export artifact

## Domain/Computation Layer
- `app/services/variography_computation_service.py` (new)
  - Wraps `compute_experimental_variogram` and future directional logic.
- `app/services/variography_model_service.py` (new)
  - Model curves/structures composition.
- `app/services/variography_validation_service.py` (new)
  - Domain-level warnings/blockers.

## Persistence/Session Layer
- `app/services/variography_persistence_service.py` (new)
  - Save/load session fragment and published artifacts.
- `app/models/variography/*.py` (new package)
  - Contracts and entity/value models.

---

## D. Variography Domain Model

## 1) VariographySession
- **Purpose:** aggregate of the active variography analysis state.
- **Key fields:**
  - `session_id`, `created_at_utc`, `updated_at_utc`
  - `dataset_file`, `analysis_context_snapshot`
  - `active_target_column`, `active_domain_filter`
  - `request`, `last_result`, `model`, `validation`
  - `dirty_flags`
- **Ownership:** VariographyApplicationService.
- **Lifecycle:** created on stage entry; updated on each accepted event; persisted optionally.

## 2) ExperimentalVariogramRequest
- **Purpose:** immutable input for experimental variogram computation.
- **Key fields:**
  - `x_col`, `y_col`, `z_col`, `target_col`
  - `domain_column`, `domain_filter`
  - `direction: DirectionDefinition`
  - `lag: LagDefinition`
  - `max_points`, `downsampling_seed`
- **Ownership:** controller builds; application service validates.
- **Lifecycle:** generated per compute-triggering event.

## 3) DirectionDefinition
- **Purpose:** encode directional variography settings.
- **Key fields:**
  - `azimuth_deg`, `dip_deg`, `azimuth_tol_deg`, `dip_tol_deg`
  - `bandwidth_h`, `bandwidth_v`
  - `is_omnidirectional`
- **Ownership:** model contract.
- **Lifecycle:** edited via UI parameter panel.

## 4) LagDefinition
- **Purpose:** encode lag geometry.
- **Key fields:**
  - `lag_size`, `n_lags`, `max_distance`
  - `min_pairs_per_lag`
- **Ownership:** model contract.
- **Lifecycle:** edited/validated before compute.

## 5) ExperimentalVariogramResult
- **Purpose:** canonical output of experimental variogram computation.
- **Key fields:**
  - `lag_centers`, `gamma_values`, `pair_counts`
  - `source_points`, `used_points`, `downsampled`
  - `warnings`, `quality_metrics` (e.g., sparse_lag_ratio)
  - `computation_hash`
- **Ownership:** computation service.
- **Lifecycle:** cached and rendered; invalidated on dirty compute inputs.

## 6) ModelStructure
- **Purpose:** one nested structure inside variogram model.
- **Key fields:**
  - `structure_type` (spherical/exponential/gaussian)
  - `range_major`, `range_minor`, `range_vertical`
  - `sill_contribution`
- **Ownership:** model service.
- **Lifecycle:** edited in structures table.

## 7) VariogramModel
- **Purpose:** full theoretical model candidate.
- **Key fields:**
  - `nugget`, `structures: list[ModelStructure]`
  - `anisotropy_definition`
  - `fit_method`, `fit_score`
- **Ownership:** model service.
- **Lifecycle:** starts empty/manual; evolves with edits/fit; validated before publish.

## 8) ModelValidationResult
- **Purpose:** standardized validation output for UI decisions.
- **Key fields:**
  - `is_valid_for_publish`
  - `warnings: list[ValidationIssue]`
  - `blockers: list[ValidationIssue]`
- **Ownership:** validation service.
- **Lifecycle:** recalculated on model/result changes.

## 9) VariographyPublishArtifact
- **Purpose:** versioned exported artifact used by downstream modules.
- **Key fields:**
  - `artifact_version`, `module_version`
  - `analysis_context_snapshot`
  - `request`, `result`, `model`, `validation`
  - `published_at_utc`, `author`, `checksum`
- **Ownership:** persistence service.
- **Lifecycle:** created only when validation has no blockers.

---

## E. Service Architecture

## Service split

### VariographyApplicationService
- Orchestrates full use-cases.
- Calls validation, computation, modeling, persistence.
- Maintains/returns session state and UI-ready DTOs.

### VariographyComputationService
- Wraps experimental computation path.
- First adapter over `compute_experimental_variogram`.
- Later: direction-aware filtering and optimized pairing.

### VariographyModelService
- Handles theoretical model lifecycle:
  - add/remove/edit structure,
  - evaluate model curve,
  - fit score calculation.

### VariographyValidationService
- Validates request parameters, result quality, and model publishability.
- Produces warnings/blockers list with machine-readable codes.

### VariographyPersistenceService
- Persists session fragments and publish artifacts.
- Exports JSON artifact and optional CSV chart data.

## Call flow (high-level)
1. UI event -> controller.
2. Controller builds request using active context snapshot.
3. Application service validates request.
4. If compute-dirty: computation service executes.
5. Model service updates/derives theoretical curves.
6. Validation service computes warnings/blockers.
7. Application service returns response for render.
8. Publish action delegates to persistence service after validation gate.

---

## F. GUI Integration Architecture

## Integration path

### Immediate path (recommended)
- Keep `HomePanel` as stage router.
- Replace `_render_variography_view` placeholder with an adapter call into `VariographyStageView` + controller.
- Keep `_build_variography_actions_inline` as lightweight host pointing to stage controller actions.

### Why not full extraction now
A full HomePanel decomposition is ideal long-term, but extracting only Variography now is lower risk and gives fast parallelization.

## Responsibilities by UI tier
- **Tk view (`VariographyStageView`):** widgets, local input text/selection, drawing containers.
- **Controller:** event mapping, request construction, refresh intent.
- **Service layer:** all computation, validation, publishability logic.

## Logic that must leave UI immediately
- Parameter validation rules.
- Any computation trigger decision beyond simple event classification.
- Publish gating rules and warning/blocker semantics.

## Component communication
- Parameter panel -> controller -> application service -> response DTO.
- Response DTO -> renderer + tables + status banner.
- No direct service calls from individual widgets.

---

## G. State Ownership Model

## UI-only ephemeral state (Tk vars allowed)
- Current form editing text not yet submitted.
- Widget selection focus and expanded/collapsed sections.
- Temporary sort/selection in tables.

## Workflow/global session state (existing)
- Dataset and resolved target context from `GeostatService` snapshot/readiness.
- Current workflow step and high-level readiness.

## Variography analysis state (new authoritative store)
- Last accepted `ExperimentalVariogramRequest`.
- Last computed `ExperimentalVariogramResult`.
- Current `VariogramModel` and `ModelValidationResult`.
- Dirty flags (`compute_dirty`, `model_dirty`, `render_dirty`).

## Persisted vs transient
- **Persisted:** publish artifacts + optional session checkpoint.
- **Transient:** in-progress unsaved UI edits, temporary chart zoom, selection state.

## State that must stop living only in Tk vars
- Lag/direction parameters considered “active compute inputs”.
- Current structures model list.
- Publish readiness/warnings/blockers.

---

## H. Event and Refresh Model

## Event rules

### 1) Variable change (target/color/domain context)
- Trigger: context changed in main workflow.
- Action: mark `compute_dirty=True`.
- Refresh: **full recompute** required.

### 2) Domain change
- Trigger: active domain filter changed.
- Action: `compute_dirty=True`.
- Refresh: **full recompute** required.

### 3) Lag parameter edit
- Trigger: lag size, n_lags, max distance change.
- Action: validate request; if valid set `compute_dirty=True`.
- Refresh: **full recompute** on apply/auto-run policy.

### 4) Direction edit
- Trigger: azimuth/dip/tolerance/bandwidth change.
- Action: validation + `compute_dirty=True`.
- Refresh: **full recompute**.

### 5) Model structure edit
- Trigger: add/remove/edit structure row.
- Action: `model_dirty=True`; recompute theoretical curve only.
- Refresh: **validation + redraw** (experimental cache reuse).

### 6) Compute action
- Trigger: explicit “Compute” button or eligible auto-compute event.
- Action: run computation if `compute_dirty=True`, else use cache.
- Refresh: **full recompute or cached reuse**.

### 7) Publish action
- Trigger: explicit publish click.
- Action: force final validation.
- Refresh: **validation-only** if blockers exist; **persist+status redraw** if pass.

## Caching key
`computation_hash = hash(dataset_signature + active_context + request)`

---

## I. Contract Layer

Below is the minimum contract needed for FE/BE parallel work.

### Compute request
```json
{
  "request_id": "uuid",
  "context": {
    "dataset_file": "string",
    "resolved_target_column": "string",
    "active_domain_column": "string|null",
    "active_domain_filter": "string|null"
  },
  "coordinates": {"x": "string", "y": "string", "z": "string"},
  "target": "string",
  "direction": {
    "is_omnidirectional": true,
    "azimuth_deg": 0.0,
    "dip_deg": 0.0,
    "azimuth_tol_deg": 90.0,
    "dip_tol_deg": 90.0,
    "bandwidth_h": null,
    "bandwidth_v": null
  },
  "lag": {
    "lag_size": 10.0,
    "n_lags": 20,
    "max_distance": 200.0,
    "min_pairs_per_lag": 30
  },
  "sampling": {"max_points": 2500, "seed": 42}
}
```

### Compute response
```json
{
  "request_id": "uuid",
  "status": "ok|warning|error",
  "result": {
    "lag_centers": [10.0, 20.0],
    "gamma_values": [0.12, 0.19],
    "pair_counts": [420, 380],
    "source_points": 12000,
    "used_points": 2500,
    "downsampled": true
  },
  "warnings": [
    {"code": "LOW_NPAIRS_LAG", "message": "Lag 18 has low npairs", "severity": "warning"}
  ],
  "validation": {
    "is_valid_for_publish": false,
    "blockers": [{"code": "INSUFFICIENT_LAG_COVERAGE", "message": "..."}],
    "warnings": []
  },
  "cache": {"computation_hash": "sha256", "from_cache": false}
}
```

### Publish response
```json
{
  "status": "published|blocked|error",
  "artifact_path": "string|null",
  "artifact_version": "v1",
  "blockers": [],
  "warnings": []
}
```

---

## J. Integration with Existing Code

- `compute_experimental_variogram` (`app/services/visualization_service.py`) -> **wrap/adapt**
  - Keep as core primitive initially via `VariographyComputationService`.
- `visualization_service.py` bundle helpers -> **reuse directly** (for first phase).
- `DashboardGrid` -> **reuse directly** for 2x2/1x2 variography layouts.
- `renderer base` (`app/ui/renderers/base.py`) -> **refactor** (add variography renderer interface).
- `get_workflow_readiness` (`GeostatService`) -> **refactor** for consistent feature readiness semantics.
- `ActivityLogService` -> **reuse directly** with new event taxonomy (`variography_compute_started`, etc.).

---

## K. Architectural Risks and Mitigations

1. **Risk:** HomePanel coupling growth.
   - **Mitigation:** variography stage extracted into dedicated view/controller modules from day 1.

2. **Risk:** Contract drift between FE/BE.
   - **Mitigation:** typed DTOs + compatibility tests + contract version field.

3. **Risk:** Compute latency (O(n²)).
   - **Mitigation:** hard max points, cache hash reuse, warnings for heavy runs, later optimization ticket.

4. **Risk:** stale state from Tk vars.
   - **Mitigation:** promote active analysis state to VariographySession and submit/apply workflow.

5. **Risk:** misleading publish state.
   - **Mitigation:** standardized validation result with blockers/warnings propagated consistently.

---

## L. Final Recommendation

### Selected architecture
**Incremental feature-layer architecture with a dedicated Variography stage module + explicit DTO contracts + application/domain service split, integrated through existing HomePanel routing.**

### Alternatives rejected
1. **Keep all logic inside HomePanel and GeostatService:** rejected due to coupling and regression risk.
2. **Full app rewrite before variography:** rejected as high-cost/high-delay and unnecessary for immediate goals.
