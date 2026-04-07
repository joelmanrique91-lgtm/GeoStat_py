from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class QaqcReport:
    total_rows: int
    valid_rows: int
    usable_pct: float
    nulls_by_column: dict[str, int]
    duplicate_collars: int
    warnings: list[str]


def validate_drillhole_data(df: pd.DataFrame, *, x: str, y: str, z: str, value: str) -> QaqcReport:
    required = [x, y, z, value]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")

    work = df[required].copy()
    for col in required:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    nulls = {col: int(work[col].isna().sum()) for col in required}
    valid = work.dropna()
    dup = int(valid.duplicated(subset=[x, y, z]).sum())
    total = len(work)
    valid_rows = len(valid)
    usable_pct = (100.0 * valid_rows / total) if total else 0.0

    warnings: list[str] = []
    if valid_rows < 30:
        warnings.append("Muestras válidas < 30, soporte bajo para variografía.")
    if dup > 0:
        warnings.append("Se detectaron collares/intervalos duplicados por XYZ.")
    if usable_pct < 80.0:
        warnings.append("Porcentaje utilizable bajo (<80%).")

    return QaqcReport(
        total_rows=total,
        valid_rows=valid_rows,
        usable_pct=usable_pct,
        nulls_by_column=nulls,
        duplicate_collars=dup,
        warnings=warnings,
    )


def composite_equal_length(
    df: pd.DataFrame,
    *,
    hole_id: str,
    from_col: str,
    to_col: str,
    value_col: str,
    length: float,
) -> pd.DataFrame:
    if length <= 0:
        raise ValueError("La longitud de compositado debe ser > 0")

    required = [hole_id, from_col, to_col, value_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas para compositado: {', '.join(missing)}")

    out_rows: list[dict[str, float | str]] = []
    work = df[required].copy()
    work[from_col] = pd.to_numeric(work[from_col], errors="coerce")
    work[to_col] = pd.to_numeric(work[to_col], errors="coerce")
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna().sort_values([hole_id, from_col, to_col])

    for hid, grp in work.groupby(hole_id):
        start = float(grp[from_col].min())
        end = float(grp[to_col].max())
        cursor = start
        while cursor < end:
            c_from = cursor
            c_to = min(cursor + length, end)
            sel = grp[(grp[to_col] > c_from) & (grp[from_col] < c_to)]
            if not sel.empty:
                weights = (sel[[to_col]].to_numpy().flatten().astype(float) - sel[[from_col]].to_numpy().flatten().astype(float))
                weights = weights.clip(min=1e-9)
                val = float((sel[value_col].to_numpy().astype(float) * weights).sum() / weights.sum())
                out_rows.append({hole_id: str(hid), from_col: c_from, to_col: c_to, value_col: val})
            cursor += length

    return pd.DataFrame(out_rows)
