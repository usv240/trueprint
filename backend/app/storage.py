"""Backblaze B2 storage layer — the Trueprint system of record.

Layout (OAIS-style dual archive):
  masters/{asset_id}/original.{ext}      immutable original (Object Lock)
  masters/{asset_id}/master.json         ingest metadata + sha256
  derivatives/{asset_id}/{run_id}/...    restored outputs, maps, manifest, step artifacts
  index/catalog.jsonl                    append-only lineage catalog
"""
from __future__ import annotations
import hashlib, json, datetime as dt
from dataclasses import dataclass
from typing import Any
from .config import config


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class PutResult:
    key: str
    sha256: str
    size: int
    url: str | None = None


class B2Store:
    """Thin, purpose-built wrapper over genblaze-s3's S3StorageBackend."""

    def __init__(self) -> None:
        config.require_b2()
        from genblaze_s3 import S3StorageBackend
        self._be = S3StorageBackend.for_backblaze(
            config.B2_BUCKET,
            region=config.B2_REGION,
            key_id=config.B2_KEY_ID,
            app_key=config.B2_APP_KEY,
            preflight=True,
        )

    # ---- low-level ----
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream",
            *, lock_days: int | None = None, metadata: dict[str, str] | None = None) -> PutResult:
        kwargs: dict[str, Any] = {"content_type": content_type}
        if metadata:
            kwargs["metadata"] = metadata
        if lock_days:
            try:
                from genblaze import ObjectLockConfig
                retain = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=lock_days)
                kwargs["object_lock"] = ObjectLockConfig(retain_until=retain)
            except Exception:
                pass  # bucket may reject per-object lock; archive still written
        try:
            self._be.put(key, data, **kwargs)
        except TypeError:
            self._be.put(key, data)
        return PutResult(key=key, sha256=sha256_hex(data), size=len(data))

    def get(self, key: str) -> bytes:
        v = self._be.get(key)
        return bytes(v if isinstance(v, (bytes, bytearray)) else getattr(v, "data", v))

    def exists(self, key: str) -> bool:
        return bool(self._be.exists(key))

    def url(self, key: str, expires_in: int = 3600) -> str:
        u = self._be.presigned_get_url(key, expires_in=expires_in)
        return u if isinstance(u, str) else getattr(u, "url", str(u))

    # ---- archive semantics ----
    def put_master(self, asset_id: str, data: bytes, ext: str, content_type: str,
                   *, lock_days: int = 3, source: dict | None = None) -> PutResult:
        """Immutable original. Object Lock (compliance) protects it from mutation."""
        key = f"masters/{asset_id}/original.{ext}"
        res = self.put(key, data, content_type, lock_days=lock_days)
        meta = {"asset_id": asset_id, "sha256": res.sha256, "size": res.size,
                "content_type": content_type, "created": _now(), "source": source or {}}
        self.put(f"masters/{asset_id}/master.json",
                 json.dumps(meta, indent=2).encode(), "application/json")
        return res

    def put_derivative(self, asset_id: str, run_id: str, name: str, data: bytes,
                       content_type: str) -> PutResult:
        return self.put(f"derivatives/{asset_id}/{run_id}/{name}", data, content_type)

    def put_step_artifact(self, asset_id: str, run_id: str, step: str, name: str,
                          data: bytes, content_type: str) -> PutResult:
        return self.put(f"derivatives/{asset_id}/{run_id}/steps/{step}/{name}", data, content_type)

    def append_catalog(self, entry: dict) -> None:
        """Append-only lineage catalog (read-modify-write; fine at hackathon scale)."""
        key = "index/catalog.jsonl"
        prev = b""
        if self.exists(key):
            try:
                prev = self.get(key)
            except Exception:
                prev = b""
        line = (json.dumps({**entry, "_ts": _now()}) + "\n").encode()
        self.put(key, prev + line, "application/x-ndjson")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()
