from __future__ import annotations

import json
from pathlib import Path

from app.models.project import ProjectState


def save_project(path: str, project: ProjectState) -> None:
    data = project.to_dict()
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(path: str) -> ProjectState:
    raw = Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    return ProjectState.from_dict(payload)
