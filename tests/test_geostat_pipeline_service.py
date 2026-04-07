from __future__ import annotations

import unittest

from workflows.variography_end_to_end_example import synthetic_anisotropic_dataset
from app.services.geostat_pipeline_service import (
    FittedVariogram,
    export_leapfrog_parameters,
    run_pipeline,
    validate_geological_data,
)


class GeostatPipelineServiceTests(unittest.TestCase):
    def test_validation_detects_duplicates_and_nulls(self) -> None:
        df = synthetic_anisotropic_dataset(n=60, seed=1)
        df.loc[0, "Au"] = None
        df.loc[1, ["X", "Y", "Z", "Au"]] = df.loc[2, ["X", "Y", "Z", "Au"]]
        report = validate_geological_data(df, "Au")
        self.assertEqual(report.total_rows, 60)
        self.assertGreaterEqual(report.nulls_by_column["Au"], 1)

    def test_run_pipeline_produces_leapfrog_export(self) -> None:
        df = synthetic_anisotropic_dataset(n=320, seed=9)
        output = run_pipeline(df, "Au", model_type="exponential")
        text = output["leapfrog_export"]
        self.assertIn("nugget=", text)
        self.assertIn("range_major=", text)
        self.assertIn("azimuth=", text)

    def test_export_includes_npairs_and_fit(self) -> None:
        df = synthetic_anisotropic_dataset(n=300, seed=10)
        output = run_pipeline(df, "Au", model_type="gaussian")
        text = export_leapfrog_parameters(FittedVariogram(**output["fitted_model"]))
        self.assertIn("fit_rmse=", text)
        self.assertIn("npairs_total=", text)


if __name__ == "__main__":
    unittest.main()
