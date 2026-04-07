from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def read_drillholes_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def write_json_trace(payload: dict[str, object], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
