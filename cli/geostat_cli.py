from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mining_geostat.io_formats import read_drillholes_csv, write_json_trace
from mining_geostat.pipeline import GeostatPipelineConfig, run_geostat_pipeline
from mining_geostat.synthetic import make_synthetic_drillholes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI mínima geoestadística")
    parser.add_argument("command", choices=["variogram", "kriging", "validate"], help="Etapa a ejecutar")
    parser.add_argument("--input-csv", default=None, help="CSV de entrada (opcional)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="datasets/output_trace.json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    df = read_drillholes_csv(args.input_csv) if args.input_csv else make_synthetic_drillholes(seed=args.seed)
    result = run_geostat_pipeline(GeostatPipelineConfig(seed=args.seed), df=df)

    if args.command == "variogram":
        payload = {
            "trace": result["trace"],
            "experimental_variogram": result["experimental_variogram"],
            "variogram_model": result["variogram_model"],
        }
    elif args.command == "kriging":
        payload = {
            "trace": result["trace"],
            "variogram_model": result["variogram_model"],
            "kriging_center": result["kriging_center"],
        }
    else:
        payload = {
            "trace": result["trace"],
            "qa_qc": result["qa_qc"],
            "cross_validation": result["cross_validation"],
        }

    write_json_trace(payload, args.out)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
