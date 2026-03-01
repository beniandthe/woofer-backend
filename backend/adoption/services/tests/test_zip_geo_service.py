from __future__ import annotations

import os
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from adoption.services.zip_geo_service import ZipGeoService


class ZipGeoServiceTests(TestCase):
    def setUp(self):
        # Ensure no cross test pollution (ZipGeoService caches per process)
        ZipGeoService.reset_cache_for_tests()

    def tearDown(self):
        ZipGeoService.reset_cache_for_tests()

    def _make_base_dir_with_csv(self, rows: str) -> str:
        """
        Creates a temp BASE_DIR with:
          adoption/data/us_zip_centroids.csv
        and writes `rows` to that CSV.
        Returns the BASE_DIR path as a string.
        """
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)

        base = Path(td.name)
        data_dir = base / "adoption" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        csv_path = data_dir / "us_zip_centroids.csv"
        csv_path.write_text(rows, encoding="utf-8")

        return str(base)

    def test_lookup_returns_lat_lon_for_known_zip(self):
        base_dir = self._make_base_dir_with_csv(
            "zip,lat,lon\n"
            "90066,33.9897,-118.4487\n"
        )

        with override_settings(BASE_DIR=Path(base_dir)):
            ZipGeoService.reset_cache_for_tests()

            res = ZipGeoService.lookup("90066")
            self.assertIsNotNone(res)
            self.assertEqual(res.postal_code, "90066")
            self.assertAlmostEqual(res.lat, 33.9897, places=4)
            self.assertAlmostEqual(res.lon, -118.4487, places=4)

    def test_lookup_normalizes_zip_plus4(self):
        base_dir = self._make_base_dir_with_csv(
            "zip,lat,lon\n"
            "90066,33.9897,-118.4487\n"
        )

        with override_settings(BASE_DIR=Path(base_dir)):
            ZipGeoService.reset_cache_for_tests()

            res = ZipGeoService.lookup("90066-1234")
            self.assertIsNotNone(res)
            self.assertEqual(res.postal_code, "90066")

    def test_lookup_returns_none_when_zip_missing_or_invalid(self):
        base_dir = self._make_base_dir_with_csv(
            "zip,lat,lon\n"
            "90066,33.9897,-118.4487\n"
        )

        with override_settings(BASE_DIR=Path(base_dir)):
            ZipGeoService.reset_cache_for_tests()

            self.assertIsNone(ZipGeoService.lookup(None))
            self.assertIsNone(ZipGeoService.lookup(""))
            self.assertIsNone(ZipGeoService.lookup("abcd"))
            self.assertIsNone(ZipGeoService.lookup("12"))  # too short
            self.assertIsNone(ZipGeoService.lookup("99999"))  # not in CSV

    def test_count_loaded_matches_rows(self):
        base_dir = self._make_base_dir_with_csv(
            "zip,lat,lon\n"
            "90066,33.9897,-118.4487\n"
            "90012,34.0614,-118.2383\n"
        )

        with override_settings(BASE_DIR=Path(base_dir)):
            ZipGeoService.reset_cache_for_tests()

            # triggers load
            _ = ZipGeoService.lookup("90066")
            self.assertEqual(ZipGeoService.count_loaded(), 2)