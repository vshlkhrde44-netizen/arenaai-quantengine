"""
Antigravity QuantEngine - Data Provenance Manifests
Cryptographically tracks the lineage, hashes, code versions, and transformations of every research dataset.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.logging import get_logger

logger = get_logger("provenance.manifest")


class DatasetProvenanceManifest(BaseModel):
    manifest_id: str
    dataset_id: str
    source_venue: str
    symbol: str
    timeframe: str
    channels: List[str]
    start_time: str
    end_time: str
    creation_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    software_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    raw_hash: str
    normalized_hash: str
    dataset_hash: str
    transformation_hash: str
    configuration_hash: str
    strategy_hash: Optional[str] = None
    preregistration_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def compute_manifest_checksum(self) -> str:
        """Compute canonical SHA-256 digest of the entire manifest."""
        canonical_dict = self.model_dump(exclude={"metadata"})
        serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def save_to_disk(self, manifests_dir: Path = Path("data/manifests")) -> Path:
        manifests_dir = Path(manifests_dir)
        manifests_dir.mkdir(parents=True, exist_ok=True)
        file_path = manifests_dir / f"manifest_{self.dataset_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.model_dump(), indent=2))
        logger.info(f"Saved dataset provenance manifest: {file_path}")
        return file_path

    @classmethod
    def load_from_disk(cls, dataset_id: str, manifests_dir: Path = Path("data/manifests")) -> Optional["DatasetProvenanceManifest"]:
        file_path = Path(manifests_dir) / f"manifest_{dataset_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
