# Variography Real-Data Test Guide (Vertical Slice)

## 1) Prerequisites
1. Python environment configured as documented in `README.md` (`conda activate geostat-py`).
2. Dependencies installed (`customtkinter`, `pandas`, `matplotlib`, etc.).
3. Real CSV dataset with numeric `X`, `Y`, `Z`, and numeric target variable.

## 2) Launch app
```bash
python -m app.main
```

## 3) Navigate to Variography
1. In **01 Datos**, load a real CSV.
2. Configure `X`, `Y`, `Z`, and target. Click **Confirmar**.
3. Click stage **06 Variografía** in the workflow bar.

## 4) Configure first experimental run
In Variography controls (left panel):
1. Select **Variable objetivo**.
2. Set parameters (example safe defaults):
   - `lag_distance = 10`
   - `n_lags = 16`
   - `lag_tolerance = 5`
   - `max_distance = 160`
   - `azimuth = 0`
   - `dip = 0`
   - `ang_tol_h = 90`
   - `ang_tol_v = 90`
   - `band_width = 0`
   - `band_height = 0`
3. Click **Compute experimental variogram**.

## 5) Expected outputs
After compute, verify all:
1. Main chart shows `gamma` vs lag centers.
2. `npairs` per lag chart is visible.
3. Diagnostic panel shows lag validity and npairs quality counts.
4. Status text shows success or warning/blocker message.
5. Warning/blocker area displays structured issue codes when applicable.

## 6) Invalid-input behavior checks
1. Set `lag_distance <= 0` or `n_lags <= 0`.
2. Compute again.
3. Confirm blockers are shown and no crash occurs.

## 7) Real-data readiness checks
1. Switch to another stage and return to Variography.
2. Confirm last parameter state and compute status remain usable for continuing workflow.
3. Recompute with updated parameters and verify deterministic update.

## 8) Known current limitation
1. Directional parameters are validated and logged but current compute path is omnidirectional.

## 9) Additional known limitations in this first slice
1. Advanced variogram model fitting/editor and publish workflow are not part of this vertical slice.
2. Compute uses capped points (`max_points=2500`) to keep responsiveness.

## 10) Troubleshooting
- **"Configura X/Y/Z/target antes de variografía"**: return to Datos and confirm columns.
- **"Target no numérico" / compute failure**: select numeric target and retry.
- **No pairs found / insufficient coverage**: increase `max_distance`, reduce `n_lags`, or use denser dataset.
- **UI shows blockers after parameter changes**: this is expected; recalculate after editing.
- **Se mantiene en “Sin cálculo aún”**: presiona **Compute experimental variogram** y revisa el panel de blockers (p.ej. formato inválido o parámetros no positivos).
