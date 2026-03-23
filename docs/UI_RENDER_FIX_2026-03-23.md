# UI Render Fix 2026-03-23

## Resumen ejecutivo
Se aplicó un hardening integral del ciclo visual (layout/render/redraw/resize) sin tocar lógica geoestadística ni contratos de servicio. El foco fue eliminar reconstrucciones innecesarias, estabilizar el embedding Matplotlib en Tk/CustomTkinter y mejorar encastre 2D/3D.

## Problemas corregidos
- Eliminación del patrón de full rebuild global de `view_body` en cada refresco.
- Eliminación de doble reconstrucción de action bar durante navegación de etapas.
- Introducción de caché por etapa y render incremental con invalidación explícita.
- Ajuste responsive real basado en tamaño útil de contenedor y resize con debounce.
- Unificación de contrato de render para evitar duplicaciones de `tight_layout/draw/pack`.
- Corrección geométrica en espacial 2D con aspect ratio consistente.
- Mejora del encastre 3D evitando recreación completa de canvas/toolbar en cada actualización.

## Causa raíz confirmada en código
La causa dominante fue el acoplamiento entre:
1. refresco global destructivo de vistas,
2. render de figuras con sizing no anclado robustamente al host,
3. responsabilidades mezcladas entre panel, grid y renderers,
4. layout 3D con conflictos de ajuste automático.

## Archivos modificados
- `app/ui/panels/home_panel.py`
- `app/ui/panels/dashboard_grid.py`
- `app/ui/panels/spatial_3d_view.py`
- `app/ui/renderers/mpl_spatial2d_renderer.py`
- `app/ui/renderers/mpl_eda_renderer.py`
- `tests/test_ui_render_hardening.py`

## Cambios implementados por archivo
### `app/ui/panels/home_panel.py`
- Introducción de hosts por etapa (`_stage_hosts`) y firmas de render (`_rendered_stage_signatures`) para evitar rebuild completo.
- Nuevo pipeline de resize de `view_body` con debounce (`_on_view_body_configure`, `_handle_view_resize`).
- `_show_stage_view` ahora reutiliza host por etapa, y solo reconstruye si cambia firma o `force_rebuild`.
- Eliminación de reconstrucción duplicada de action bar en `_render_step`.
- Invalidación selectiva de caché de etapa tras cambios de datos/config/filtros.
- Rework de renderers de etapa (`_render_eda_view`, `_render_cutoff_view`, `_render_spatial_view`, `_render_domains_view`) para separar refresh de datos/layout.

### `app/ui/panels/dashboard_grid.py`
- Render responsivo con binding a `<Configure>` del widget canvas.
- Debounce de resize y ajuste de `Figure.set_size_inches(...)` al tamaño real del host.
- Uso de `draw_idle()` para minimizar repaints costosos.
- Evita repacking redundante del canvas.

### `app/ui/panels/spatial_3d_view.py`
- Persistencia de figura/canvas/toolbar por widget 3D (evita recreación completa por refresh menor).
- Update de nube mediante limpieza/reconstrucción interna del contenido de figura, no del widget host.
- Reemplazo de `tight_layout` por `subplots_adjust` en 3D para encastre estable con colorbar.

### `app/ui/renderers/mpl_spatial2d_renderer.py`
- Se fuerza lectura geométrica válida en XY/XZ/YZ con límites cuadrados y `set_aspect("equal")`.

### `app/ui/renderers/mpl_eda_renderer.py`
- Se unifica contrato de render: renderer delega cierre visual en `DashboardGrid.render()`.

### `tests/test_ui_render_hardening.py`
- Regresiones para:
  - no doble rebuild de action bar desde `_render_step`,
  - aspect ratio explícito en espacial 2D,
  - resize debounce y `draw_idle` en `DashboardGrid`.

## Decisiones técnicas importantes
- Se priorizó compatibilidad: no se alteró lógica científica ni contratos del service layer.
- Se aplicó caching/invalidation conservador por etapa para evitar stale data.
- Se evitó reescritura total de UI y se preservó estructura funcional existente.

## Riesgos evitados
- Evitado tearing/flicker por destrucción global en cada refresh.
- Evitada duplicación de draw/layout que producía geometría no determinista.
- Evitada recreación completa de widget 3D en updates menores.

## Qué NO se tocó
- Cálculos geoestadísticos.
- Contratos de servicios y modelos.
- Flujo funcional y nombres de etapas.
- Branding/estilo visual general.

## Resultado esperado en runtime
- Transiciones entre etapas más limpias y estables.
- Menos recortes/deformaciones por resize.
- Mejor proporcionalidad geométrica en espacial 2D.
- Vista 3D mejor encastrada y con menor sensación de reconstrucción.
- Menor costo de repaint al redimensionar y al refrescar.

## Lista de tests ejecutados
- `python -m pytest -q`
