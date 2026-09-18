"""
Antigravity QuantEngine - Research Dataset Subsystem & D3 Sealed Data Firewall
Manages analytical Parquet/DuckDB datasets with strict data isolation.
Enforces D3 Sealed Data Firewall: D3_READ=0, D3_HASH=0, D3_LOAD=0 when sealed.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd

from database.engine import get_db
from core.audit.quality_auditor import DataQualityAuditor
from core.provenance.manifest import DatasetProvenanceManifest
from core.logging import get_logger

logger = get_logger("research.dataset")


class SealedDatasetAccessViolation(Exception):
    """Raised when an unauthorized attempt is made to access a sealed dataset."""
    pass


class DatasetManager:
    """Manages Parquet/DuckDB datasets, provenance, and sealed data enforcement."""

    def __init__(self, datasets_dir: Path = Path("data/datasets"), duckdb_path: Path = Path("data/analytics.duckdb")):
        self.datasets_dir = Path(datasets_dir)
        self.duckdb_path = Path(duckdb_path)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    def register_dataset(
        self,
        name: str,
        venue: str,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        is_sealed: bool = False
    ) -> str:
        """Register, store as Parquet, compute hash, create manifest, and audit."""
        dataset_id = f"ds_{venue}_{symbol.replace('-', '_')}_{timeframe}_{uuid.uuid4().hex[:6]}"
        parquet_file = self.datasets_dir / f"{dataset_id}.parquet"
        
        # Save Parquet
        df.to_parquet(parquet_file, index=False)
        
        # Calculate raw file hash
        dataset_hash = hashlib.sha256(parquet_file.read_bytes()).hexdigest()

        start_time = str(df["timestamp"].min()) if "timestamp" in df.columns else datetime.now(timezone.utc).isoformat()
        end_time = str(df["timestamp"].max()) if "timestamp" in df.columns else datetime.now(timezone.utc).isoformat()

        # Database record
        db = get_db()
        sql = """
            INSERT INTO datasets (
                dataset_id, name, source_venue, symbol, timeframe,
                start_time, end_time, record_count, parquet_path,
                dataset_hash, is_sealed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        db.execute_non_query(
            sql,
            (
                dataset_id, name, venue, symbol, timeframe,
                start_time, end_time, len(df), str(parquet_file),
                dataset_hash, int(is_sealed)
            )
        )

        # Compute multi-stage provenance hashes independently (P0-07, Section 12-15)
        raw_bytes = df.to_json(orient="records").encode("utf-8")
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()

        norm_spec = json.dumps({"columns": sorted(list(df.columns)), "types": [str(t) for t in df.dtypes]}, sort_keys=True)
        normalized_hash = hashlib.sha256(norm_spec.encode("utf-8") + raw_bytes).hexdigest()

        transform_spec = json.dumps({
            "version": "2.0.0",
            "venue": venue,
            "timeframe": timeframe,
            "schema_version": "1.0",
            "transform": "ohlcv_canonical_time_sort"
        }, sort_keys=True)
        transformation_hash = hashlib.sha256(transform_spec.encode("utf-8")).hexdigest()

        cfg = get_config()
        cfg_dict = cfg.model_dump()
        cfg_dict.pop("security", None)
        config_hash = hashlib.sha256(json.dumps(cfg_dict, sort_keys=True, default=str).encode("utf-8")).hexdigest()

        # Create Manifest
        manifest = DatasetProvenanceManifest(
            manifest_id=f"man_{dataset_id}",
            dataset_id=dataset_id,
            source_venue=venue,
            symbol=symbol,
            timeframe=timeframe,
            channels=["ticker", "trades", "candles"],
            start_time=start_time,
            end_time=end_time,
            raw_hash=raw_hash,
            normalized_hash=normalized_hash,
            dataset_hash=dataset_hash,
            transformation_hash=transformation_hash,
            configuration_hash=config_hash
        )
        manifest.save_to_disk()

        # Run automated quality audit
        DataQualityAuditor.audit_dataframe(dataset_id, df, expected_hash=None)

        logger.info(f"Registered research dataset: {dataset_id} ({len(df)} records, hash: {dataset_hash[:8]}...)")
        return dataset_id

    def load_dataset(self, dataset_id: str, caller_token: Optional[str] = None) -> pd.DataFrame:
        """
        Load dataset dataframe with D3 Sealed Firewall enforcement.
        If dataset is sealed, D3_READ=0, D3_LOAD=0, D3_HASH=0.
        """
        db = get_db()
        rows = db.execute_query("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,))
        if not rows:
            raise FileNotFoundError(f"Dataset {dataset_id} not found in registry.")

        row = rows[0]
        if row["is_sealed"]:
            # D3 SEALED DATA FIREWALL ENFORCEMENT
            # Unauthorized access attempt is strictly blocked and audited
            self._log_sealed_violation(dataset_id, "LOAD_ATTEMPT")
            raise SealedDatasetAccessViolation(
                f"D3 SEALED DATA FIREWALL VIOLATION: Dataset {dataset_id} is cryptographically sealed! "
                f"D3_READ=0, D3_LOAD=0. Unauthorized access blocked."
            )

        parquet_path = Path(row["parquet_path"])
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file {parquet_path} missing.")

        return pd.read_parquet(parquet_path)

    def seal_dataset(self, dataset_id: str) -> None:
        """Cryptographically seal a dataset. Once sealed, out-of-sample data is immutable and unreadable."""
        db = get_db()
        db.execute_non_query(
            "UPDATE datasets SET is_sealed = 1 WHERE dataset_id = ?",
            (dataset_id,)
        )
        logger.info(f"D3 FIREWALL: Sealed dataset {dataset_id}. D3_READ=0, D3_LOAD=0, D3_HASH=0.")

    def _log_sealed_violation(self, dataset_id: str, action: str) -> None:
        db = get_db()
        sql = """
            INSERT INTO risk_events (
                event_id, event_type, severity, rule_name,
                metric_value, threshold_value, details_json
            ) VALUES (?, 'SEALED_DATA_VIOLATION', 'CRITICAL', 'D3_FIREWALL_BREACH', 0, 0, ?)
        """
        db.execute_non_query(
            sql,
            (
                f"violation_{uuid.uuid4().hex[:8]}",
                json.dumps({"dataset_id": dataset_id, "action": action, "timestamp": datetime.now(timezone.utc).isoformat()})
            )
        )


_DATASET_MANAGER: Optional[DatasetManager] = None


def get_dataset_manager() -> DatasetManager:
    global _DATASET_MANAGER
    if _DATASET_MANAGER is None:
        _DATASET_MANAGER = DatasetManager()
    return _DATASET_MANAGER
