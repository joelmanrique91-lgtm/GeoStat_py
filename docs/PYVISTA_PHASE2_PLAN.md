# PyVista Phase 2 Pilot Plan (Controlled)

## Current decision
PyVista is wired as an optional 3D backend candidate, but **not enabled yet**.

## Why not enabled in this phase
- Repo UI stack is `CustomTkinter` + Tk event loop.
- Interactive embedded PyVista requires a reliable Tk bridge / event-loop strategy.
- This pilot keeps system behavior safe by falling back to the existing Matplotlib 3D renderer.

## What was prepared
- `PyVistaSpatial3DRenderer` implementing `Spatial3DRenderer` interface.
- HomePanel backend selection hook with fallback logging.
- No change to calculation/workflow/data contracts.

## Enablement criteria for next phase
1. Confirm import/runtime support for `pyvista` and `vtk` in target environment.
2. Implement and validate non-blocking interactive embedding strategy compatible with Tk.
3. Add targeted tests for backend selection and runtime fallback paths.
