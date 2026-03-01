from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
import csv
import threading

from django.conf import settings


LatLon = Tuple[float, float]


@dataclass(frozen=True)
class ZipGeoResult:
    postal_code: str
    lat: float
    lon: float


class ZipGeoService:
    """
    Deterministic offline ZIP -> (lat, lon) lookup.
    - No network calls
    - No DB writes
    - CSV loaded once per process (thread-safe)
    """

    _lock = threading.Lock()
    _cache: Optional[Dict[str, LatLon]] = None

    @staticmethod
    def normalize_zip(z: Optional[str]) -> Optional[str]:
        if not z:
            return None
        s = str(z).strip()
        if not s:
            return None
        # Keep only digits, accept "12345-6789" and similar
        digits = "".join(ch for ch in s if ch.isdigit())
        if len(digits) < 5:
            return None
        return digits[:5]

    @classmethod
    def _csv_path(cls) -> Path:
        # ship a small static dataset in repo 
        # Default location: backend/adoption/data/us_zip_centroids.csv
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        return base_dir / "adoption" / "data" / "us_zip_centroids.csv"

    @classmethod
    def _load(cls) -> Dict[str, LatLon]:
        path = cls._csv_path()
        if not path.exists():
            # Hard fail would break callers - return empty so callers can degrade gracefully
            return {}

        out: Dict[str, LatLon] = {}
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            # Expected headers zip, lat, lon 
            for row in reader:
                if not isinstance(row, dict):
                    continue
                z = cls.normalize_zip(row.get("zip") or row.get("ZIP") or row.get("postal_code") or row.get("postal"))
                if not z:
                    continue
                lat_raw = row.get("lat") or row.get("LAT") or row.get("latitude")
                lon_raw = row.get("lon") or row.get("LON") or row.get("longitude") or row.get("lng")
                try:
                    lat = float(lat_raw)
                    lon = float(lon_raw)
                except (TypeError, ValueError):
                    continue
                out[z] = (lat, lon)

        return out

    @classmethod
    def _ensure_cache(cls) -> None:
        if cls._cache is not None:
            return
        with cls._lock:
            if cls._cache is None:
                cls._cache = cls._load()

    @classmethod
    def lookup(cls, postal_code: Optional[str]) -> Optional[ZipGeoResult]:
        z = cls.normalize_zip(postal_code)
        if not z:
            return None

        cls._ensure_cache()
        assert cls._cache is not None

        latlon = cls._cache.get(z)
        if not latlon:
            return None

        lat, lon = latlon
        return ZipGeoResult(postal_code=z, lat=lat, lon=lon)

    @classmethod
    def count_loaded(cls) -> int:
        cls._ensure_cache()
        assert cls._cache is not None
        return len(cls._cache)

    @classmethod
    def reset_cache_for_tests(cls) -> None:
        # Only intended for unit tests
        with cls._lock:
            cls._cache = None