# Variography Integration Plan

## Phase 0 - Stabilization prerequisites

### Objective
Prepare safe integration rails so variography work does not amplify current coupling.

### Scope
- Freeze minimum DTO contracts for compute/validate/publish.
- Define state ownership rules (Tk ephemeral vs analysis authoritative state).
- Correct readiness semantics for disabled vs implemented stages.

### Dependencies
- Audit artifacts:
  - `docs/CODEBASE_AUTOAUDIT.md`
  - `docs/GUI_UX_TECHNICAL_AUDIT.md`
  - `docs/AUDIT_INVENTORY.json`

### Likely files/modules touched
- `app/services/geostat_service.py` (readiness semantics)
- `app/models/` (new variography contracts package)
- `docs/` (contract spec)

### Risks
- Overdesign before implementation.
- Backward compatibility noise in readiness tests.

### Exit criteria
- Contract v1 documented and agreed.
- Readiness contract includes feature availability semantics.
- State ownership policy documented and approved.

---

## Phase 1 - Backend/domain foundation

### Objective
Build variography backend core independently from UI rendering details.

### Scope
- Add contracts:
  - `ExperimentalVariogramRequest`
  - `ExperimentalVariogramResult`
  - `ModelValidationResult`
  - `VariographyPublishArtifact`
- Implement services:
  - `VariographyApplicationService`
  - `VariographyComputationService` (wrap existing primitive)
  - `VariographyValidationService`
  - `VariographyPersistenceService` skeleton

### Dependencies
- Phase 0 contract freeze.

### Likely files/modules touched
- `app/services/variography_*.py` (new)
- `app/models/variography/*.py` (new)
- `app/services/visualization_service.py` (adapter-level integration points only)
- `tests/` new backend tests

### Risks
- Mismatch between current `GeostatService` snapshot and new request builder expectations.
- Performance surprises on large datasets.

### Exit criteria
- Backend service can compute experimental variogram from dataset/context snapshot.
- Validation produces warnings/blockers codes.
- Persistence skeleton can serialize artifact contract (even if publish UI not ready).

---

## Phase 2 - UI shell integration

### Objective
Wire real variography stage in UI without full HomePanel rewrite.

### Scope
- Add `VariographyStageView` and `VariographyController`.
- Replace placeholder render path in `_render_variography_view`.
- Keep stage routing in `HomePanel`; delegate stage internals.
- Introduce chart/table containers using `DashboardGrid` and renderer adapter.

### Dependencies
- Phase 1 application service and contracts available.

### Likely files/modules touched
- `app/ui/panels/home_panel.py`
- `app/ui/panels/stages/variography_stage_view.py` (new)
- `app/ui/controllers/variography_controller.py` (new)
- `app/ui/renderers/base.py` (variography interface)
- `app/ui/renderers/mpl_variography_renderer.py` (new)

### Risks
- Interface drift if controller/view contracts are unstable.
- HomePanel regression due to integration points.

### Exit criteria
- Variography stage displays real parameter panel and response-driven chart placeholders.
- No direct computation logic remains in view widgets.
- Existing Datos/EDA/Cutoffs/Espacial flows remain intact.

---

## Phase 3 - Experimental variography workflow

### Objective
Deliver end-to-end experimental variography interaction loop.

### Scope
- Compute action -> request -> result -> rendering.
- Lag and direction parameter edits with deterministic refresh policy.
- Display npairs diagnostics and low-quality warnings.
- Cache reuse for non-compute-changing events.

### Dependencies
- Phase 2 UI shell integration.

### Likely files/modules touched
- `app/services/variography_application_service.py`
- `app/services/variography_computation_service.py`
- `app/ui/controllers/variography_controller.py`
- `app/ui/renderers/mpl_variography_renderer.py`
- new tests for flow and cache logic

### Risks
- Inconsistent dirty-flag handling.
- User confusion if auto-compute vs explicit compute policy is mixed.

### Exit criteria
- Experimental chart, npairs chart, warnings banner fully operational.
- Event-driven refresh matrix implemented and tested.
- Activity log events emitted for compute lifecycle.

---

## Phase 4 - Modeling workflow

### Objective
Add theoretical model authoring/validation without destabilizing experimental workflow.

### Scope
- Structures table with nugget + nested structures.
- Model curve overlay on experimental points.
- Validation engine for publish blockers.
- Model fit score visibility.

### Dependencies
- Phase 3 experimental result contract stable.

### Likely files/modules touched
- `app/services/variography_model_service.py`
- `app/services/variography_validation_service.py`
- `app/ui/panels/stages/variography_stage_view.py`
- `app/ui/renderers/mpl_variography_renderer.py`

### Risks
- Model parameter explosion and UX overload (non-polish scope now).
- Validation criteria disputes.

### Exit criteria
- Users can build/edit at least one model with deterministic validation output.
- Publish readiness state shows blockers/warnings from standardized codes.

---

## Phase 5 - Publish and traceability

### Objective
Enable controlled publish/export of variography artifacts with full traceability.

### Scope
- Implement artifact versioning and checksum.
- Persist publish artifact JSON and optional derived tables.
- Extend activity log event taxonomy for publish lifecycle.
- Expose export hooks for downstream workflows.

### Dependencies
- Phase 4 validation stable.

### Likely files/modules touched
- `app/services/variography_persistence_service.py`
- `app/services/activity_log_service.py` (event usage only)
- `app/services/geostat_service.py` (if orchestration bridge needed)
- docs for artifact schema and compatibility

### Risks
- Artifact schema churn if not version-locked.
- Downstream consumers not yet aligned.

### Exit criteria
- Publish operation blocked when blockers exist, succeeds when clear.
- Versioned artifact generated and re-loadable.
- Audit trail includes compute/model/publish chain.

---

## Parallelization strategy

### Can be developed in parallel
- Backend contracts/services (Phase 1) and UI shell scaffolding (Phase 2) after contract freeze.
- Renderer implementation and controller wiring once response DTOs are fixed.
- Validation rules and publish UI messaging with shared issue-code catalog.

### Must remain sequential
- Contract freeze (Phase 0) before serious parallel FE/BE.
- Experimental compute flow (Phase 3) before modeling (Phase 4).
- Validation publish blockers before final publish integration (Phase 5).

---

## Recommended branch strategy

- `feature/variography-contracts-v1` (Phase 0/1)
- `feature/variography-backend-core` (Phase 1)
- `feature/variography-ui-shell` (Phase 2)
- `feature/variography-experimental-flow` (Phase 3)
- `feature/variography-modeling` (Phase 4)
- `feature/variography-publish` (Phase 5)

Guideline:
- Merge contracts branch first.
- Rebase downstream branches onto latest contracts/tests baseline.
- Keep each phase behind small, testable PR slices.
