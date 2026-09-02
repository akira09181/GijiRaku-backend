"""Runtime switches for low-cost deployments without Firestore quota."""

from __future__ import annotations

import os

MEMORY_STORAGE_BACKEND = "memory-fallback"
FIRESTORE_STORAGE_BACKEND = "firestore"


def prefer_memory_store() -> bool:
    """When true, skip Firestore for citizen-facing ephemeral stores."""
    return os.getenv("GIJIRAKU_PREFER_MEMORY_STORE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def active_storage_backend() -> str:
    return MEMORY_STORAGE_BACKEND if prefer_memory_store() else FIRESTORE_STORAGE_BACKEND
