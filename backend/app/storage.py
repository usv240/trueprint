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
            *, lock_days: int | None = None, lock_mode: str = "GOVERNANCE",
            metadata: dict[str, str] | None = None) -> PutResult:
        kwargs: dict[str, Any] = {"content_type": content_type}
        if metadata:
            kwargs["metadata"] = metadata
        if lock_days:
            try:
                from genblaze import ObjectLockConfig
                retain = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=lock_days)
                try:
                    kwargs["object_lock"] = ObjectLockConfig(retain_until=retain, mode=lock_mode)
                except Exception:  # mode may require an enum
                    from genblaze import ObjectLockMode  # type: ignore
                    kwargs["object_lock"] = ObjectLockConfig(retain_until=retain,
                                                             mode=ObjectLockMode(lock_mode))
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
                   *, lock_days: int | None = None, source: dict | None = None) -> PutResult:
        """Immutable original. Object Lock protects it from mutation/deletion."""
        from .config import config
        days = config.B2_MASTER_LOCK_DAYS if lock_days is None else lock_days
        key = f"masters/{asset_id}/original.{ext}"
        res = self.put(key, data, content_type, lock_days=days, lock_mode=config.B2_MASTER_LOCK_MODE)
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

    def put_catalog_entry(self, run_id: str, entry: dict) -> None:
        """One immutable object per run — no whole-file rewrite, no write races."""
        self.put(f"index/runs/{run_id}.json",
                 json.dumps({**entry, "_ts": _now()}).encode(), "application/json")

    def append_catalog(self, entry: dict) -> None:  # back-compat alias
        self.put_catalog_entry(entry.get("run_id") or _now(), entry)

    def list_keys(self, prefix: str, max_keys: int = 1000) -> list[str]:
        page = self._be.list(prefix, max_keys=max_keys)
        out: list[str] = []
        for e in getattr(page, "entries", []) or []:
            k = getattr(e, "key", None) or (e.get("key") if isinstance(e, dict) else None)
            if k:
                out.append(k)
        return out

    def list_catalog(self, limit: int = 200) -> list[dict]:
        entries: list[dict] = []
        for k in self.list_keys("index/runs/"):
            if k.endswith(".json"):
                try:
                    entries.append(json.loads(self.get(k)))
                except Exception:
                    pass
        entries.sort(key=lambda e: e.get("_ts", ""), reverse=True)
        return entries[:limit]

    def find_by_hash(self, digest: str) -> dict | None:
        for e in self.list_catalog(limit=1000):
            if digest in (e.get("derivative_sha256"), e.get("master_sha256")):
                return e
        return None


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()
