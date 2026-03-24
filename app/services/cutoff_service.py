"""Specialized service for cutoff preview and application flows."""

from __future__ import annotations

import math
import statistics


def _is_numeric_dtype(series) -> bool:
    from pandas.api.types import is_numeric_dtype

    return bool(is_numeric_dtype(series))


def _to_numeric(series):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce")


class CutoffService:
    """Encapsulates cutoff validation, preview and apply operations."""

    def __init__(self, host_service) -> None:
        self.host = host_service

    def has_confirmed_dynamic_capping(self) -> bool:
        return bool(self.host.workflow_state.dynamic_cutoff_enabled and self.host.workflow_state.dynamic_cutoff_output_column)

    def clear_cutoff_state(self) -> None:
        self.host.workflow_state.cutoffs_enabled = False
        self.host.workflow_state.cutoff_target_column = ""
        self.host.workflow_state.cutoff_limits = []
        self.host.workflow_state.cutoff_labels = []
        self.host.workflow_state.cutoff_output_column = ""
        self.host.workflow_state.effective_target_column = ""

    def clear_dynamic_cutoff_state(self) -> None:
        self.host.workflow_state.dynamic_cutoff_enabled = False
        self.host.workflow_state.dynamic_cutoff_target_column = ""
        self.host.workflow_state.dynamic_cutoff_mode = "percentile"
        self.host.workflow_state.dynamic_cutoff_percent = 95.0
        self.host.workflow_state.dynamic_cutoff_value = 0.0
        self.host.workflow_state.dynamic_cutoff_output_column = ""
        self.host.workflow_state.dynamic_cutoff_category_column = ""

    def format_cutoff_number(self, value: float) -> str:
        try:
            numeric = float(value)
        except Exception:
            return str(value)
        return f"{numeric:.6g}"

    def parse_cutoff_limits(self, limits_text: str) -> tuple[list[float], str]:
        values = [segment.strip() for segment in str(limits_text).split(",") if segment.strip()]
        if not values:
            return [], "Debes ingresar al menos un límite numérico."
        try:
            limits = sorted({float(value) for value in values})
        except ValueError:
            return [], "Los límites deben ser números válidos separados por coma."
        return limits, ""

    def build_cutoff_labels(self, limits: list[float]) -> list[str]:
        if len(limits) == 1:
            c0 = self.format_cutoff_number(limits[0])
            return [f"< {c0}", f">= {c0}"]
        labels: list[str] = [f"< {self.format_cutoff_number(limits[0])}"]
        for left, right in zip(limits[:-1], limits[1:]):
            labels.append(f"[{self.format_cutoff_number(left)}, {self.format_cutoff_number(right)})")
        labels.append(f">= {self.format_cutoff_number(limits[-1])}")
        return labels

    def prepare_dynamic_cutoff_preview(self, target_column: str, mode: str, slider_percent: float) -> dict[str, object]:
        if self.host.current_dataset is None:
            raise ValueError("No hay dataset cargado.")
        if target_column not in self.host.current_dataset.columns:
            raise ValueError("La variable seleccionada no existe en el dataset.")

        numeric = _to_numeric(self.host.current_dataset.dataframe[target_column]).dropna().astype(float)
        if numeric.empty:
            raise ValueError("La variable seleccionada no tiene valores numéricos válidos.")

        values = numeric.tolist()
        min_val = float(numeric.min())
        max_val = float(numeric.max())
        slider_clamped = max(0.0, min(100.0, float(slider_percent)))
        if mode == "absolute":
            cutoff = min_val + ((max_val - min_val) * (slider_clamped / 100.0))
        else:
            cutoff = float(numeric.quantile(slider_clamped / 100.0))

        retained = numeric[numeric <= cutoff]
        truncated = numeric[numeric > cutoff]
        capped = numeric.clip(upper=cutoff)
        capped_max = float(min(max_val, cutoff))
        percentile_at_cutoff = float((numeric <= cutoff).sum() / len(numeric) * 100.0)

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        normal = statistics.NormalDist()
        theoretical = [normal.inv_cdf((idx + 0.5) / n) for idx in range(n)] if n > 1 else [0.0]

        return {
            "values": values,
            "sorted_values": sorted_vals,
            "theoretical_quantiles": theoretical,
            "cutoff_value": float(cutoff),
            "min": min_val,
            "max": max_val,
            "affected_count": int(len(truncated)),
            "affected_pct": float((len(truncated) / len(values)) * 100.0),
            "retained_pct": percentile_at_cutoff,
            "retained_values": retained.tolist(),
            "truncated_values": truncated.tolist(),
            "capped_values": capped.tolist(),
            "max_original": max_val,
            "max_truncated": capped_max,
        }

    def apply_dynamic_cutoff(
        self,
        *,
        enabled: bool,
        target_column: str,
        mode: str,
        slider_percent: float,
        output_column: str | None = None,
        keep_category_column: bool = True,
    ) -> tuple[bool, str, float]:
        if self.host.current_dataset is None:
            return False, "No hay dataset cargado.", 0.0
        if self.host.variable_config is None:
            return False, "Configura X/Y/Z/target antes de aplicar capping.", 0.0
        if not enabled:
            self.clear_dynamic_cutoff_state()
            return True, "Capping dinámico desactivado.", 0.0

        try:
            preview = self.prepare_dynamic_cutoff_preview(target_column, mode, slider_percent)
        except ValueError as exc:
            return False, str(exc), 0.0

        cutoff = float(preview["cutoff_value"])
        out_col = (output_column or f"{target_column}_capped").strip()
        if out_col in {self.host.variable_config.x_column, self.host.variable_config.y_column, self.host.variable_config.z_column}:
            return False, "El nombre de salida no puede sobrescribir X/Y/Z.", 0.0

        source = _to_numeric(self.host.current_dataset.dataframe[target_column])
        self.host.current_dataset.dataframe[out_col] = source.clip(upper=cutoff)
        if out_col not in self.host.current_dataset.columns:
            self.host.current_dataset.columns.append(out_col)
            self.host.current_dataset.column_count = len(self.host.current_dataset.columns)

        category_col = ""
        if keep_category_column:
            category_col = f"{out_col}_class"
            labels = [f"<= {self.format_cutoff_number(cutoff)}", f"> {self.format_cutoff_number(cutoff)}"]
            import pandas as pd

            self.host.current_dataset.dataframe[category_col] = pd.cut(source, bins=[-math.inf, cutoff, math.inf], labels=labels, right=True, include_lowest=True)
            if category_col not in self.host.current_dataset.columns:
                self.host.current_dataset.columns.append(category_col)
                self.host.current_dataset.column_count = len(self.host.current_dataset.columns)

        self.host.workflow_state.dynamic_cutoff_enabled = True
        self.host.workflow_state.dynamic_cutoff_target_column = target_column
        self.host.workflow_state.dynamic_cutoff_mode = "absolute" if mode == "absolute" else "percentile"
        self.host.workflow_state.dynamic_cutoff_percent = float(max(0.0, min(100.0, slider_percent)))
        self.host.workflow_state.dynamic_cutoff_value = cutoff
        self.host.workflow_state.dynamic_cutoff_output_column = out_col
        self.host.workflow_state.dynamic_cutoff_category_column = category_col
        self.host.workflow_state.effective_target_column = out_col
        self.host.activity_log.log(
            "dynamic_cutoff_applied",
            "success",
            "Capping dinámico aplicado.",
            {
                "target": target_column,
                "mode": self.host.workflow_state.dynamic_cutoff_mode,
                "slider_percent": self.host.workflow_state.dynamic_cutoff_percent,
                "cutoff_value": cutoff,
                "output_column": out_col,
                "category_column": category_col,
            },
        )
        return True, f"Capping aplicado. Nueva variable: {out_col}", cutoff

    def apply_cutoffs(self, *, enabled: bool, target_column: str, limits_text: str, output_column: str | None = None) -> tuple[bool, str]:
        if self.host.current_dataset is None:
            return False, "No hay dataset cargado."
        if self.host.variable_config is None:
            return False, "Configura X/Y/Z/target antes de aplicar Control de Outliers."

        if not enabled:
            self.clear_cutoff_state()
            self.host.workflow_state.effective_target_column = self.host.variable_config.target_column
            self.host.activity_log.log("cutoff_disabled", "info", "Control de Outliers manual desactivado. Se usa target original.", {"target": self.host.variable_config.target_column})
            return True, "Control de Outliers manual desactivado. Se mantiene variable original."

        if target_column not in self.host.current_dataset.columns:
            return False, "La variable seleccionada no existe en el dataset."
        if not _is_numeric_dtype(self.host.current_dataset.dataframe[target_column]):
            return False, "La variable seleccionada debe ser numérica."

        limits, parse_error = self.parse_cutoff_limits(limits_text)
        if parse_error:
            return False, parse_error

        labels = self.build_cutoff_labels(limits)
        output_name = (output_column or f"{target_column}_cutoff").strip()
        if output_name in {self.host.variable_config.x_column, self.host.variable_config.y_column, self.host.variable_config.z_column}:
            return False, "El nombre de salida no puede sobrescribir X/Y/Z."

        import pandas as pd

        source = _to_numeric(self.host.current_dataset.dataframe[target_column])
        bins = [-math.inf, *limits, math.inf]
        categorized = pd.cut(source, bins=bins, labels=labels, right=False, include_lowest=True)
        self.host.current_dataset.dataframe[output_name] = categorized
        if output_name not in self.host.current_dataset.columns:
            self.host.current_dataset.columns.append(output_name)
            self.host.current_dataset.column_count = len(self.host.current_dataset.columns)

        self.host.workflow_state.cutoffs_enabled = True
        self.host.workflow_state.cutoff_target_column = target_column
        self.host.workflow_state.cutoff_limits = limits
        self.host.workflow_state.cutoff_labels = labels
        self.host.workflow_state.cutoff_output_column = output_name
        self.host.workflow_state.effective_target_column = output_name

        self.clear_dynamic_cutoff_state()
        self.host.activity_log.log(
            "cutoff_applied",
            "success",
            "Límites manuales de Control de Outliers aplicados.",
            {
                "target": target_column,
                "limits": limits,
                "labels": labels,
                "output_column": output_name,
            },
        )
        return True, f"Control de Outliers aplicado. Nueva variable categórica: {output_name}"
