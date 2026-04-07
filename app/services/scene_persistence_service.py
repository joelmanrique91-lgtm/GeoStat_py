"""Lightweight JSON persistence for SceneState."""

from __future__ import annotations

from pathlib import Path

from app.models.spatial import SceneState


class ScenePersistenceService:
    def save(self, scene: SceneState, destination: str) -> str:
        path = Path(destination)
        path.write_text(scene.to_json(), encoding="utf-8")
        return str(path)

    def load(self, source: str) -> SceneState:
        path = Path(source)
        return SceneState.from_json(path.read_text(encoding="utf-8"))
