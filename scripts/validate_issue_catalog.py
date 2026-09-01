"""Deployment gate for the public issue catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from issue_catalog import validate_issue_catalog  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(validate_issue_catalog(), ensure_ascii=False, indent=2))
