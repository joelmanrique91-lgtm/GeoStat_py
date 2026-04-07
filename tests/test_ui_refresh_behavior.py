from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models.spatial import PointCloudGeometry, SceneLayer, SceneState
from app.ui.controllers.spatial_viewer_controller import SpatialViewerController
from app.ui.panels.home_panel import HomePanel
from app.ui.panels.spatial_3d_view import Spatial3DView
from app.ui.renderers.mpl_variography_renderer import MatplotlibVariographyRenderer


class _FakeCanvas:
    def __init__(self) -> None:
        self.draw_idle_calls = 0

    def draw_idle(self) -> None:
        self.draw_idle_calls += 1


class _FakeMetaLabel:
    def __init__(self) -> None:
        self._text = ""

    def configure(self, *, text: str) -> None:
        self._text = text

    def cget(self, _name: str) -> str:
        return self._text


class _FakeFigure:
    def __init__(self) -> None:
        self.size_calls: list[tuple[float, float, bool]] = []

    def get_dpi(self) -> float:
        return 100.0

    def set_size_inches(self, w: float, h: float, forward: bool = False) -> None:
        self.size_calls.append((w, h, forward))


class _FakeHost:
    def __init__(self, width: int = 1000, height: int = 700) -> None:
        self._w = width
        self._h = height

    def winfo_width(self) -> int:
        return self._w

    def winfo_height(self) -> int:
        return self._h


class _FakeGrid:
    def __init__(self) -> None:
        self.render_calls = 0
        self.canvas = _FakeCanvas()
        self.figure = type("Fig", (), {})()

    def axis(self, _r: int, _c: int):
        class _Axis:
            def __init__(self) -> None:
                self.calls = []

            def plot(self, *args, **kwargs):
                self.calls.append(("plot", args, kwargs))

            def scatter(self, *args, **kwargs):
                self.calls.append(("scatter", args, kwargs))

            def bar(self, *args, **kwargs):
                self.calls.append(("bar", args, kwargs))
                return []

            def set_title(self, *_args, **_kwargs):
                return None

            def set_xlabel(self, *_args, **_kwargs):
                return None

            def set_ylabel(self, *_args, **_kwargs):
                return None

            def legend(self, *_args, **_kwargs):
                return None

            def axhline(self, *_args, **_kwargs):
                return None

            def axvline(self, *_args, **_kwargs):
                return None

            def axis(self, *_args, **_kwargs):
                return None

            def text(self, *_args, **_kwargs):
                return None

        return _Axis()

    def render(self) -> None:
        self.render_calls += 1


class _StubWidget:
    def __init__(self, master) -> None:
        self.master = master
        self._exists = True
        self.grid_calls = 0

    def grid(self, **_kwargs) -> None:
        self.grid_calls += 1

    def winfo_exists(self) -> bool:
        return self._exists

    def destroy(self) -> None:
        self._exists = False


class _StubRenderer:
    def __init__(self) -> None:
        self.created = 0

    def is_available(self):
        return True, "ok"

    def create_widget(self, parent):
        self.created += 1
        return _StubWidget(parent)

    def render(self, widget, scene, color_display_label):
        _ = (widget, scene, color_display_label)

    def show_unavailable(self, widget, reason):
        _ = (widget, reason)


class UIRefreshBehaviorTests(unittest.TestCase):
    def test_variography_single_draw(self) -> None:
        renderer = MatplotlibVariographyRenderer()
        grid = _FakeGrid()
        with patch("app.ui.renderers.mpl_variography_renderer.apply_axis_style", lambda _ax: None):
            renderer.render(
                grid,
                {
                    "lag_centers": [1.0, 2.0, 3.0],
                    "gamma_values": [0.1, 0.2, 0.3],
                    "pair_counts": [40, 45, 42],
                    "source_points": 10,
                    "used_points": 10,
                    "downsampled": False,
                    "metadata": {},
                },
                type("Ctx", (), {"target_label": "target", "info_text": "ok", "chart_text_color": "#fff", "chart_label_size": 10, "chart_legend_size": 9})(),
            )
        self.assertEqual(grid.render_calls, 1)
        self.assertEqual(grid.canvas.draw_idle_calls, 0)

    def test_spatial3d_single_draw_scene_update(self) -> None:
        view = Spatial3DView.__new__(Spatial3DView)
        view._axis = None
        view._canvas = _FakeCanvas()
        view.meta_label = _FakeMetaLabel()
        called_finalize: list[bool] = []

        def _fake_update_cloud(_bundle, _label, *, point_size=None, point_alpha=None, finalize_draw=True):
            _ = (point_size, point_alpha)
            called_finalize.append(bool(finalize_draw))
            view._axis = object()

        view.update_cloud = _fake_update_cloud  # type: ignore[method-assign]
        view._render_scene_overlays = lambda _scene: None  # type: ignore[method-assign]
        payload = PointCloudGeometry(
            points_xyz=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            color_values=(1.0, 2.0),
            color_mode="numeric",
            color_label="target",
            source_point_count=2,
            rendered_point_count=2,
        )
        scene = SceneState(
            layers=(
                SceneLayer(
                    layer_id="points",
                    layer_type="point_cloud",
                    visible=True,
                    opacity=0.9,
                    color_by="target",
                    display_name="Points",
                    payload=payload,
                    style={"size": 7.0},
                ),
            ),
            active_variable="target",
            active_domain="Todos",
        )
        Spatial3DView.update_scene(view, scene, "target")
        self.assertEqual(called_finalize, [False])
        self.assertEqual(view._canvas.draw_idle_calls, 1)

    def test_data_refresh_reuses_host(self) -> None:
        controller = SpatialViewerController(service=type("Svc", (), {"current_dataset": None, "get_analysis_context_snapshot": lambda _self: {}, "get_dataset_revision": lambda _self: 0, "get_context_revision": lambda _self: 0})())
        controller.build_or_get_scene = lambda **_kwargs: SceneState(layers=(), active_variable="x", active_domain="Todos")  # type: ignore[method-assign]
        renderer = _StubRenderer()
        parent = object()
        widget = _StubWidget(parent)
        first = controller.render_scene(parent=parent, renderer=renderer, color_by="x", existing_widget=widget)
        second = controller.render_scene(parent=parent, renderer=renderer, color_by="x", existing_widget=widget)
        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(renderer.created, 0)

    def test_resize_same_size_no_redraw(self) -> None:
        view = Spatial3DView.__new__(Spatial3DView)
        view._resize_after_id = None
        view._figure = _FakeFigure()
        view._canvas = _FakeCanvas()
        view.plot_host = _FakeHost(width=1000, height=700)
        view._last_plot_size = None
        view._last_size_inches = None
        Spatial3DView._sync_figure_to_host(view, force=False)
        Spatial3DView._sync_figure_to_host(view, force=False)
        self.assertEqual(view._canvas.draw_idle_calls, 1)

    def test_rebuild_only_on_structure_change(self) -> None:
        panel = HomePanel.__new__(HomePanel)
        panel.view_body = _FakeHost(width=1200, height=800)
        panel._get_stage_signature = lambda _stage: ("stable",)  # type: ignore[method-assign]
        plan_data = HomePanel._build_refresh_plan(panel, stage="Espacial", reason="spatial_style_changed", force=False)
        plan_structure = HomePanel._build_refresh_plan(panel, stage="Espacial", reason="step_render", force=False)
        self.assertFalse(plan_data.requires_rebuild)
        self.assertTrue(plan_data.requires_data_refresh)
        self.assertTrue(plan_structure.requires_rebuild)


if __name__ == "__main__":
    unittest.main()
