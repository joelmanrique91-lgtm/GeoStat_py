"""Unit tests for variography operational reliability classification."""

from __future__ import annotations

import unittest

from app.services.variography_validation_service import FitReliability, classify_operational_reliability


class VariographyValidationServiceTests(unittest.TestCase):
    def test_classification_blocked_when_blockers_present(self) -> None:
        fit = FitReliability(level="high", flags=[], notes=[], metrics={})
        status = classify_operational_reliability(
            fit_reliability=fit,
            blockers_count=1,
            total_pairs=100,
            valid_lags=8,
        )
        self.assertEqual(status.classification, "BLOCKED")

    def test_classification_exploratory_only_for_low_pairs(self) -> None:
        fit = FitReliability(level="high", flags=[], notes=[], metrics={})
        status = classify_operational_reliability(
            fit_reliability=fit,
            blockers_count=0,
            total_pairs=20,
            valid_lags=2,
        )
        self.assertEqual(status.classification, "EXPLORATORY_ONLY")

    def test_classification_low_reliability_for_medium_or_low_fit(self) -> None:
        fit = FitReliability(level="medium", flags=["HIGH_RELATIVE_RMSE"], notes=[], metrics={})
        status = classify_operational_reliability(
            fit_reliability=fit,
            blockers_count=0,
            total_pairs=200,
            valid_lags=9,
        )
        self.assertEqual(status.classification, "LOW_RELIABILITY")

    def test_classification_acceptable_preliminary(self) -> None:
        fit = FitReliability(level="high", flags=[], notes=[], metrics={})
        status = classify_operational_reliability(
            fit_reliability=fit,
            blockers_count=0,
            total_pairs=250,
            valid_lags=10,
        )
        self.assertEqual(status.classification, "ACCEPTABLE_PRELIMINARY")


if __name__ == "__main__":
    unittest.main()

