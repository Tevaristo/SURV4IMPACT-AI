from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = PROJECT_ROOT / "work" / "matrix_build"


def _read_json(name: str) -> Any:
    path = KNOWLEDGE_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Base de conhecimento em falta: {path}. "
            "Mantenha a pasta work/matrix_build junto da aplicação."
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    return _read_json("catalog.json")


@lru_cache(maxsize=1)
def load_pilot_rules() -> list[dict[str, Any]]:
    return _read_json("pilot_rules.json")


@lru_cache(maxsize=1)
def load_support_data() -> dict[str, Any]:
    return _read_json("support_data.json")


def p0_catalog() -> list[dict[str, Any]]:
    return [item for item in load_catalog() if item.get("priority") == "P0"]


def criterion_label(criterion_id: str) -> str:
    for item in load_catalog():
        if item.get("id") == criterion_id:
            return str(item.get("item", criterion_id))
    return criterion_id

