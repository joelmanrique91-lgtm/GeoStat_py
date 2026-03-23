"""Contract tests for variography DTOs."""

from __future__ import annotations

import unittest

from app.models.variography import (
    AnalysisContextRef,
    DirectionDefinition,
    ExperimentalVariogramRequest,
    LagDefinition,
    SCHEMA_VERSION,
)


class VariographyContractsTests(unittest.TestCase):
    def test_request_contract_has_required_fields(self) -> None:
        req = ExperimentalVariogramRequest(
            schema_version=SCHEMA_VERSION,
            context=AnalysisContextRef(dataset_file="a.csv", resolved_target_column="target"),
            x_col="x",
            y_col="y",
            z_col="z",
            target_col="target",
            lag=LagDefinition(10.0, 16, 5.0, 160.0),
            direction=DirectionDefinition(0.0, 0.0, 90.0, 90.0, 0.0, 0.0),
        )
        self.assertEqual(req.schema_version, SCHEMA_VERSION)
        self.assertEqual(req.target_col, "target")
        self.assertEqual(req.lag.n_lags, 16)
        self.assertEqual(req.direction.ang_tol_h, 90.0)


if __name__ == "__main__":
    unittest.main()
