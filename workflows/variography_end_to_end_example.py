"""Reproducible end-to-end example for geostatistical pipeline."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.services.geostat_pipeline_service import run_pipeline


def synthetic_anisotropic_dataset(n: int = 450, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.0, 500.0, n)
    y = rng.uniform(0.0, 500.0, n)
    z = rng.uniform(0.0, 120.0, n)

    trend_major = np.sin((x * 0.020) + (y * 0.007))
    trend_minor = 0.35 * np.cos((y * 0.030) + (z * 0.012))
    nugget_noise = rng.normal(0.0, 0.12, n)
    grade = 1.8 + 0.9 * trend_major + trend_minor + nugget_noise

    return pd.DataFrame({"X": x, "Y": y, "Z": z, "Au": grade})


def main() -> None:
    df = synthetic_anisotropic_dataset()
    output = run_pipeline(df, "Au", model_type="spherical")
    print("=== QA/QC ===")
    print(json.dumps(output["qa_qc"], indent=2, ensure_ascii=False))
    print("\n=== EDA ===")
    print(json.dumps(output["eda"], indent=2, ensure_ascii=False))
    print("\n=== FITTED MODEL ===")
    print(json.dumps(output["fitted_model"], indent=2, ensure_ascii=False))
    print("\n=== LEAPFROG EXPORT ===")
    print(output["leapfrog_export"])


if __name__ == "__main__":
    main()
