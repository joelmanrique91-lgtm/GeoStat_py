"""Typed logical scene state and lightweight JSON persistence helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json

from .camera_state import CameraState
from .clipping_state import ClippingState
from .scene_layer import SceneLayer


@dataclass(frozen=True)
class SceneState:
    layers: tuple[SceneLayer, ...]
    active_variable: str
    active_domain: str
    active_selection: str = ""
    camera_state: CameraState = field(default_factory=CameraState)
    clipping_state: ClippingState = field(default_factory=ClippingState)
    render_mode: str = "3d"
    context_key: str = ""
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    diagnostics: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def from_dict(payload: dict[str, object]) -> "SceneState":
        from .scene_layer import SceneLayer

        layers_payload = payload.get("layers", [])
        layers: list[SceneLayer] = []
        for entry in layers_payload if isinstance(layers_payload, list) else []:
            if not isinstance(entry, dict):
                continue
            layers.append(
                SceneLayer(
                    layer_id=str(entry.get("layer_id", "")),
                    layer_type=str(entry.get("layer_type", "point_cloud")),
                    visible=bool(entry.get("visible", True)),
                    opacity=float(entry.get("opacity", 1.0)),
                    color_by=str(entry.get("color_by")) if entry.get("color_by") is not None else None,
                    display_name=str(entry.get("display_name", "Layer")),
                    payload=entry.get("payload", ()),
                    style=dict(entry.get("style", {})) if isinstance(entry.get("style", {}), dict) else {},
                )
            )
        camera_payload = payload.get("camera_state", {})
        clip_payload = payload.get("clipping_state", {})
        return SceneState(
            layers=tuple(layers),
            active_variable=str(payload.get("active_variable", "")),
            active_domain=str(payload.get("active_domain", "")),
            active_selection=str(payload.get("active_selection", "")),
            camera_state=CameraState(**camera_payload) if isinstance(camera_payload, dict) else CameraState(),
            clipping_state=ClippingState(**clip_payload) if isinstance(clip_payload, dict) else ClippingState(),
            render_mode=str(payload.get("render_mode", "3d")),
            context_key=str(payload.get("context_key", "")),
            timestamp_utc=str(payload.get("timestamp_utc", datetime.now(timezone.utc).isoformat())),
            diagnostics=dict(payload.get("diagnostics", {})) if isinstance(payload.get("diagnostics", {}), dict) else {},
        )

    @staticmethod
    def from_json(raw: str) -> "SceneState":
        return SceneState.from_dict(json.loads(raw))
