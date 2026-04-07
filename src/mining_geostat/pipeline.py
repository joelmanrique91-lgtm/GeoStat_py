from __future__ import annotations

from dataclasses import asdict, dataclass

from .kriging import NeighborhoodConfig, ordinary_kriging
from .qa_qc import validate_drillhole_data
from .synthetic import make_synthetic_drillholes
from .validation import leave_one_out_cv
from .variogram import experimental_variogram_3d, fit_variogram_model


@dataclass(frozen=True)
class GeostatPipelineConfig:
    seed: int = 7
    lag: float = 25.0
    n_lags: int = 12
    max_distance: float = 300.0
    azimuth: float = 35.0
    dip: float = 0.0
    ang_tol_h: float = 25.0
    ang_tol_v: float = 25.0
    bandwidth: float = 80.0
    model_type: str = "spherical"
    min_samples: int = 4
    max_samples: int = 12


def run_geostat_pipeline(config: GeostatPipelineConfig, df=None) -> dict[str, object]:
    data = make_synthetic_drillholes(seed=config.seed) if df is None else df

    qc = validate_drillhole_data(data, x="X", y="Y", z="Z", value="grade")
    exp = experimental_variogram_3d(
        data,
        x="X",
        y="Y",
        z="Z",
        value="grade",
        lag=config.lag,
        n_lags=config.n_lags,
        max_distance=config.max_distance,
        azimuth=config.azimuth,
        dip=config.dip,
        ang_tol_h=config.ang_tol_h,
        ang_tol_v=config.ang_tol_v,
        bandwidth=config.bandwidth,
        seed=config.seed,
    )
    model = fit_variogram_model(exp, model_type=config.model_type)

    xyz = data[["X", "Y", "Z"]].to_numpy(dtype=float)
    values = data["grade"].to_numpy(dtype=float)
    neigh = NeighborhoodConfig(min_samples=config.min_samples, max_samples=config.max_samples)

    target = xyz.mean(axis=0)
    ok = ordinary_kriging(xyz, values, target, model, neigh)
    cv = leave_one_out_cv(xyz, values, model, neigh)

    return {
        "trace": {
            "seed": config.seed,
            "variogram_params": asdict(config),
            "neighborhood": asdict(neigh),
        },
        "qa_qc": asdict(qc),
        "experimental_variogram": asdict(exp),
        "variogram_model": asdict(model),
        "kriging_center": asdict(ok),
        "cross_validation": asdict(cv),
    }
