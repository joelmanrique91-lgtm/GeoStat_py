# Variography Test Strategy

This strategy defines must-have testing to implement variography safely in the current codebase.

## A. Test layers

## 1) Unit tests
- Focus: pure DTO validation helpers, mappers, dirty-flag transitions, issue-code formatting.
- Target modules:
  - `app/models/variography/*`
  - `app/services/variography_context_mapper.py`
  - `app/services/variography_validation_service.py`

## 2) Service tests
- Focus: application service orchestration and compute/model/publish behavior.
- Target modules:
  - `app/services/variography_application_service.py`
  - `app/services/variography_computation_service.py`
  - `app/services/variography_model_service.py`
  - `app/services/variography_persistence_service.py`

## 3) Integration tests
- Focus: controller + stage view + app service interaction with mocked renderer where needed.
- Target modules:
  - `app/ui/controllers/variography_controller.py`
  - `app/ui/panels/stages/variography_stage_view.py`

## 4) UI behavior tests
- Focus: event-to-refresh behavior, warning/blocker rendering, publish gating.
- Existing style: AST/behavior tests in `tests/test_ui_*`.
- New file: `tests/test_variography_ui_behavior.py`.

## 5) Regression tests
- Focus: ensure Datos/EDA/Cutoffs/Espacial and workflow readiness remain stable.
- Extend:
  - `tests/test_workflow_state.py`
  - `tests/test_visual_preparation.py`
  - `tests/test_ui_render_hardening.py`
  - `tests/test_ui_geometry_manager.py`

---

## B. Backend test matrix

| Area | Scenario | Expected outcome | Test type |
|---|---|---|---|
| Request validation | missing x/y/z/target | blocker code `INVALID_CONTEXT_COLUMNS` | unit/service |
| Request validation | lag_size <= 0 | blocker code `INVALID_LAG_DEFINITION` | unit |
| Request validation | n_lags <= 0 | blocker code `INVALID_LAG_DEFINITION` | unit |
| Lag handling | valid lag config | compute succeeds and returns lag arrays length n_lags | service |
| Direction handling | omnidirectional | succeeds | service |
| Direction handling | unsupported directional mode | warning/blocker deterministic code | service |
| Warnings | low npairs in tail lags | warning `LOW_NPAIRS_LAG` present | service |
| Blockers | no pairs in all lags | blocker `INSUFFICIENT_LAG_COVERAGE` | service |
| Caching | same request hash twice | second response `from_cache=true` | service |
| Caching | parameter change | recompute path executed | service |
| Publish validation | blockers exist | publish blocked status | service |
| Publish validation | no blockers | artifact created and path returned | service |
| PSD validation | PSD check fail | blocker `PSD_VALIDATION_FAILED` | service |
| Persistence | artifact load version mismatch | deterministic error code | service |

Notes:
- Use deterministic synthetic datasets (fixed seed) for repeatability.
- Keep dataset sizes small for CI; one medium benchmark scenario optional in non-gating tests.

---

## C. Frontend test matrix

| Area | Scenario | Expected outcome | Test type |
|---|---|---|---|
| Stage initialization | navigate to Variography | stage view mounted via HomePanel router | integration |
| Parameter edits | lag field change | `compute_dirty=true` and compute button enabled | UI behavior |
| Parameter edits | model structure edit | `model_dirty=true`, no forced compute | UI behavior |
| Compute action | click Compute with valid request | charts render + status success | integration |
| Compute action | click Compute with invalid request | blocker panel shown, no crash | integration |
| Dirty flags | compute then model edit | redraw/validation-only path | UI behavior |
| Refresh semantics | non-compute edit | redraw-only, no compute service call | UI behavior |
| Refresh semantics | compute-dirty edit | recompute service call | UI behavior |
| Warnings rendering | warnings returned | warning banner list rendered with codes | UI behavior |
| Blockers rendering | blockers returned | publish disabled + blocker panel shown | UI behavior |
| Publish action | blocked state | no publish call performed | UI behavior |
| Publish action | ready state | publish call fired and success message shown | integration |

---

## D. Contract tests

## Objective
Guarantee DTO compatibility across UI/controller/service boundaries.

## Required contract test cases
1. `ExperimentalVariogramRequest` required fields and type validation.
2. `ExperimentalVariogramResult` field presence (`lag_centers`, `gamma_values`, `pair_counts`, flags).
3. Validation issue schema (`code`, `message`, `severity`, `path`).
4. Publish response schema (`status`, `artifact_path`, `artifact_version`, issues).
5. Contract version compatibility test (fail on breaking changes without version bump).

## Suggested test file
- `tests/test_variography_contracts.py`

---

## E. Regression tests

## Workflow/regression coverage checklist
1. Stage switching across all tabs remains functional.
2. Existing EDA/Cutoffs/Spatial renders still execute after variography integration.
3. `get_workflow_readiness()` contract remains backward-compatible for non-variography consumers.
4. Existing AST-based UI hardening tests continue to pass or are intentionally updated with rationale.
5. Activity logging behavior for existing flows remains unchanged.

## Existing test files to protect/extend
- `tests/test_workflow_state.py`
- `tests/test_visual_preparation.py`
- `tests/test_ui_render_hardening.py`
- `tests/test_ui_geometry_manager.py`
- `tests/test_service_features.py`

---

## F. Minimum must-pass suite before merge

## Must-pass for P0/P1 feature PRs
1. `tests/test_variography_contracts.py` (new)
2. `tests/test_variography_services.py` (new)
3. `tests/test_variography_ui_behavior.py` (new)
4. `tests/test_workflow_state.py`
5. `tests/test_visual_preparation.py`
6. `tests/test_ui_render_hardening.py`
7. `tests/test_ui_geometry_manager.py`

## Merge gate policy
- No PR merging with failing contract tests.
- No PR merging if regression suite fails for existing tabs.
- For publish-related PRs, publish blocker tests must pass (including PSD validation hook tests).

---

## Test data strategy

- Add deterministic fixture datasets under `tests/fixtures/variography/`:
  - `variography_small_numeric.csv`
  - `variography_sparse_pairs.csv`
  - `variography_invalid_context.csv`
  - `variography_publish_ready.csv`
  - `variography_publish_blocked.csv`
- Ensure each fixture maps to at least one matrix scenario.

---

## CI execution recommendation

- **Fast lane (per PR):** contract + critical service + targeted UI behavior subset.
- **Full lane (nightly or pre-release):** full service matrix + regression suite + optional compute benchmark smoke.
