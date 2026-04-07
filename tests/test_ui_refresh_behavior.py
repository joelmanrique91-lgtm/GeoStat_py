from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models.spatial import PointCloudGeometry, SceneLayer, SceneState
from app.ui.controllers.spatial_viewer_controller import SpatialViewerController
from app.ui.panels.dashboard_grid import DashboardGrid
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
    class _Var:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

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

    def test_eda_data_refresh_reuses_grid(self) -> None:
        panel = HomePanel.__new__(HomePanel)
        signature = ("sig",)
        panel._build_eda_render_signature = lambda _op: signature  # type: ignore[method-assign]
        panel._get_stage_signature = lambda _stage: None  # type: ignore[method-assign]
        panel._set_stage_signature = lambda _stage, _sig: None  # type: ignore[method-assign]
        panel.eda_use_capping_var = self._Var(False)
        panel.target_var = self._Var("target")
        panel.eda_secondary_visible_var = self._Var(False)
        panel._get_active_eda_plots = lambda: ["histogram"]  # type: ignore[method-assign]
        panel._eda_payload_cache = {signature: ({"target_values": [1.0, 2.0], "diagnostics": {}}, {"skewness": "0.1"})}
        calls: list[tuple[str, object]] = []
        panel.eda_renderer = type("R", (), {"render_panel": lambda _self, **kwargs: calls.append(("render", kwargs["grid"]))})()
        grid = DashboardGrid.__new__(DashboardGrid)
        parent = type("P", (), {"winfo_children": lambda _self: []})()
        panel._eda_incremental_state = {id(parent): {"structure_signature": (False, ("histogram",)), "primary_grid": grid, "secondary_grids": {}}}
        panel.service = type(
            "Svc",
            (),
            {
                "get_operational_state": lambda _self: type(
                    "Op",
                    (),
                    {
                        "cutoff": type("Cut", (), {"effective_target_column": "target", "dynamic_enabled": False, "dynamic_cutoff_value": 0.0})(),
                        "analysis": type("An", (), {"active_domain_column": "", "active_domain_filter": ""})(),
                    },
                )(),
            },
        )()
        panel._parse_cv_ratio = lambda _raw: 0.1  # type: ignore[method-assign]
        panel._dynamic_wraplength = lambda: 800  # type: ignore[method-assign]
        panel._button_style = lambda _role="aux": {}  # type: ignore[method-assign]
        clear_calls: list[int] = []
        with patch("app.ui.panels.home_panel.DashboardGrid.clear", lambda _p: clear_calls.append(1)):
            HomePanel._render_eda_view(panel, parent, force_rebuild=False, data_refresh=True)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1], grid)
        self.assertEqual(clear_calls, [])

    def test_spatial2d_data_refresh_reuses_grid(self) -> None:
        panel = HomePanel.__new__(HomePanel)
        panel.spatial_color_var = self._Var("target")
        panel._spatial_payload_cache = {
            ("spatial2d", "target", "", "target"): type("Res", (), {"success": True, "spatial_data": object(), "message": ""})()
        }
        parent = type("P", (), {})()
        panel._spatial2d_incremental_state = {id(parent): {"signature": ("spatial2d", "target", "", "target"), "grid": DashboardGrid.__new__(DashboardGrid)}}
        rendered: list[object] = []
        panel.spatial_2d_renderer = type("R", (), {"render": lambda _self, grid, spatial, context: rendered.append(grid)})()
        panel.service = type("Svc", (), {"get_analysis_context_snapshot": lambda _self: {"active_domain_filter": "", "resolved_target_column": "target"}, "get_cutoff_state": lambda _self: {}})()
        HomePanel._render_spatial_2d_view(panel, parent, data_refresh=True)
        self.assertEqual(len(rendered), 1)
        self.assertIs(rendered[0], panel._spatial2d_incremental_state[id(parent)]["grid"])

    def test_refresh_plan_not_decorative(self) -> None:
        panel = HomePanel.__new__(HomePanel)
        panel.workspace_title_var = self._Var("")
        panel.workspace_subtitle_var = self._Var("")
        panel._display_step_name = lambda x: x  # type: ignore[attr-defined]
        panel.service = type("Svc", (), {"get_workflow_readiness_state": lambda _self: type("R", (), {"stages": {"eda": type("S", (), {"ready": True})(), "spatial": type("S", (), {"ready": True})(), "variography": type("S", (), {"ready": True})(), "cutoffs": type("S", (), {"ready": True})(), "domains": type("S", (), {"ready": True})(), "data": type("S", (), {"ready": True})()}})()})()
        panel._render_eda_view_called = False
        panel._render_spatial_view_called = False
        panel._render_variography_view_called = False
        panel._invalidate_stage_cache_called = False
        panel._render_eda_view = lambda *_args, **kwargs: setattr(panel, "_render_eda_view_called", kwargs.get("data_refresh", False))  # type: ignore[method-assign]
        panel._render_spatial_view = lambda *_args, **kwargs: setattr(panel, "_render_spatial_view_called", kwargs.get("data_refresh", False))  # type: ignore[method-assign]
        panel._render_variography_view = lambda *_args, **_kwargs: setattr(panel, "_render_variography_view_called", True)  # type: ignore[method-assign]
        panel._invalidate_stage_cache = lambda *_args, **_kwargs: setattr(panel, "_invalidate_stage_cache_called", True)  # type: ignore[method-assign]
        stage_host = type("H", (), {})()
        HomePanel._render_stage_ready_view(panel, "EDA", stage_host, force_rebuild=False, data_refresh=True)
        HomePanel._render_stage_ready_view(panel, "Espacial", stage_host, force_rebuild=False, data_refresh=True)
        HomePanel._render_stage_ready_view(panel, "Variografía", stage_host, force_rebuild=False, data_refresh=True)
        self.assertTrue(panel._render_eda_view_called)
        self.assertTrue(panel._render_spatial_view_called)
        self.assertTrue(panel._render_variography_view_called)
        self.assertTrue(panel._invalidate_stage_cache_called)


if __name__ == "__main__":
    unittest.main()
