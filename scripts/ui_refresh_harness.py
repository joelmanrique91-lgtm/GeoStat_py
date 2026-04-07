"""Manual harness to inspect UI refresh lifecycle logs.

Run:
    python -m scripts.ui_refresh_harness
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.adapters.geostatspy_adapter import GeostatSpyAdapter
from app.services.activity_log_service import ActivityLogService
from app.services.geostat_service import GeostatService
from app.ui.main_window import MainWindow


def _seed_dataset(path: Path) -> None:
    path.write_text(
        "x,y,z,target,hole,domain\n"
        "0,0,0,1,A,D1\n"
        "1,1,1,2,A,D1\n"
        "2,1,2,3,B,D2\n"
        "3,2,3,4,B,D2\n"
        "4,3,4,5,C,D1\n",
        encoding="utf-8",
    )


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    service = GeostatService(adapter=GeostatSpyAdapter(), activity_log=ActivityLogService())
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv = Path(tmp_dir) / "harness.csv"
        _seed_dataset(csv)
        service.load_csv(str(csv))
        service.set_variable_config("x", "y", "z", "target", hole_id_column="hole", domain_column="domain")
        win = MainWindow(service=service)
        root = win.root
        root.after(200, lambda: service.set_workflow_step("EDA"))
        root.after(450, lambda: service.set_workflow_step("Espacial"))
        root.after(700, lambda: service.set_workflow_step("Variografía"))
        root.after(950, lambda: root.geometry("1200x780"))
        root.after(1150, lambda: root.geometry("1200x780"))
        root.after(1450, lambda: root.destroy())
        root.mainloop()


if __name__ == "__main__":
    main()
