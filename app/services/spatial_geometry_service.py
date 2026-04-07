"""Build typed spatial geometries from current dataset/context.

This service intentionally uses best-effort trajectory/interval construction from
sample points because full survey/deviation tables are not available in the current
product scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.spatial import AssayIntervals3D, DrillholeTrajectory, PointCloudGeometry


@dataclass(frozen=True)
class SpatialGeometryPayload:
    point_cloud: PointCloudGeometry
    drillholes: tuple[DrillholeTrajectory, ...]
    assay_intervals: tuple[AssayIntervals3D, ...]


class SpatialGeometryService:
    def build_geometry(
        self,
        dataframe,
        *,
        x_col: str,
        y_col: str,
        z_col: str,
        color_col: str,
        hole_id_col: str | None,
        color_mode: str,
        color_tick_positions: list[float] | None,
        color_tick_labels: list[str] | None,
    ) -> SpatialGeometryPayload:
        clean = dataframe[[col for col in [x_col, y_col, z_col, color_col, hole_id_col] if col]].dropna()
        points_xyz = tuple((float(r[x_col]), float(r[y_col]), float(r[z_col])) for _, r in clean.iterrows())
        color_values = tuple(float(v) for v in clean[color_col].tolist())
        point_cloud = PointCloudGeometry(
            points_xyz=points_xyz,
            color_values=color_values,
            color_mode=color_mode,
            color_label=color_col,
            color_tick_positions=tuple(color_tick_positions or ()),
            color_tick_labels=tuple(color_tick_labels or ()),
            source_point_count=int(len(clean)),
            rendered_point_count=int(len(clean)),
        )

        if not hole_id_col or hole_id_col not in clean.columns:
            return SpatialGeometryPayload(point_cloud=point_cloud, drillholes=(), assay_intervals=())

        drillholes: list[DrillholeTrajectory] = []
        assay_intervals: list[AssayIntervals3D] = []
        grouped = clean.groupby(hole_id_col, dropna=True)
        for hole_id, group in grouped:
            hole_df = group.sort_values(z_col, ascending=False)
            hole_points = tuple((float(r[x_col]), float(r[y_col]), float(r[z_col])) for _, r in hole_df.iterrows())
            if len(hole_points) >= 2:
                drillholes.append(
                    DrillholeTrajectory(
                        hole_id=str(hole_id),
                        points_xyz=hole_points,
                        metadata={"approximation": "sorted_by_z", "samples": len(hole_points)},
                    )
                )

                segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
                from_to: list[tuple[float, float]] = []
                values: list[float] = []
                for idx in range(len(hole_points) - 1):
                    p0 = hole_points[idx]
                    p1 = hole_points[idx + 1]
                    segments.append((p0, p1))
                    from_to.append((p0[2], p1[2]))
                    values.append((float(hole_df.iloc[idx][color_col]) + float(hole_df.iloc[idx + 1][color_col])) * 0.5)
                assay_intervals.append(
                    AssayIntervals3D(
                        hole_id=str(hole_id),
                        from_to=tuple(from_to),
                        values=tuple(values),
                        segments_xyz=tuple(segments),
                        variable_name=color_col,
                        metadata={"approximation": "consecutive_sample_segments"},
                    )
                )

        return SpatialGeometryPayload(
            point_cloud=point_cloud,
            drillholes=tuple(drillholes),
            assay_intervals=tuple(assay_intervals),
        )
