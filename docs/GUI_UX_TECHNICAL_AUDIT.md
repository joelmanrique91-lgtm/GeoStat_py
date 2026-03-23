# GUI / UX TECHNICAL AUDIT (GeoStat_py)

## A. Current screen map
### Pantallas/etapas visibles
1. **01 Datos**
   - Definición: `HomePanel._show_stage_view -> stage == "Datos"`.
   - Controles: `_build_data_actions_inline`, `_build_data_controls`.
2. **02 EDA**
   - Definición: `_render_eda_view`.
   - Controles: `_build_eda_actions_inline`, `_build_eda_controls`.
3. **03 Cutoffs**
   - Definición: `_render_cutoff_view` + `_render_cutoff_preview_plots`.
   - Controles: `_build_cutoff_actions_inline`, `_build_cutoff_decision_controls`, `_build_cutoff_controls`.
4. **04 Espacial**
   - Definición: `_render_spatial_view` con submodo **2D/3D**.
   - Controles: `_build_spatial_actions_inline`, `_build_spatial_controls`.
5. **05 Dominios**
   - Definición: `_render_domains_view` (placeholder deshabilitado).
6. **06 Variografía**
   - Definición: `_render_variography_view` (placeholder “en construcción”).

### Navegación
- Botones de etapa en `_build_step_progress`.
- Cambio con `_on_change_step` -> `service.set_workflow_step` -> `_render_step`.
- Sin router externo; navegación local en una sola ventana/panel.

## B. Component map
### Componentes reutilizables principales
- `DashboardGrid` (`app/ui/panels/dashboard_grid.py`): wrapper figura+axes+canvas, clear/destroy centralizados, debounce resize.
- Theme tokens/utilidades (`app/ui/theme.py`): paleta, tipografías, helper de estilo axis/figure.
- Renderers abstraídos (`app/ui/renderers/base.py`): interfaces de EDA, spatial 2D, spatial 3D.

### Componentes de gráficos
- `MatplotlibEDARenderer` (`mpl_eda_renderer.py`): hist, QQ, boxplot, overlays de cutoff.
- `MatplotlibSpatial2DRenderer` (`mpl_spatial2d_renderer.py`): XY/XZ/YZ + colorbar + ficha técnica.
- `Spatial3DView` (`spatial_3d_view.py`): nube 3D embebida con toolbar.
- `MatplotlibSpatial3DRenderer` y `PyVistaSpatial3DRenderer`: estrategia fallback por disponibilidad.

### Componentes de filtros y formularios
- Selectores/menus inline y panel auxiliar (`_selector`, `_selector_inline`, `_build_*_controls`).
- Switches/slider para cutoff dinámico/manual.
- Filtros de dominio presentes en UI pero backend de dominios deshabilitado.

### Tablas/grillas
- EDA stats como tabla derivada de `service.get_target_statistics_table` (se consume como map, no widget tabla especializada).
- No se detecta grid/tabulator dedicado para datasets grandes.

## C. Interaction model
### Cableado de eventos
- Estilo callback imperativo por widget.
- Ejemplos:
  - Carga CSV: `_on_load_csv`.
  - Config variables: `_on_apply_config`.
  - Capping: `_on_apply_cutoffs`, `_on_apply_dynamic_cutoff`, `_on_slider_change`.
  - Espacial: `_on_spatial_mode_changed`, `_on_spatial_color_changed`.
- Telemetría UI en `_trace_ui_action`.

### Propagación filtros -> charts
- Dominio espacial: `_on_apply_domain_filter` llama `service.set_active_domain`, pero servicio lo neutraliza (módulo deshabilitado), por lo que no filtra realmente.
- Color by espacial: sí propaga (`prepare_visual_data(color_by=...)`).
- EDA with capping: switch local altera target efectivo para preparación EDA.

### Sincronización de estado
- Múltiples fuentes:
  - variables Tk de UI,
  - `service.workflow_state`,
  - dataframe en memoria.
- Sin transacciones de estado; sincronización vía llamadas manuales `_refresh_dashboard` + invalidación de cache.

### Riesgos de stale UI / race
1. Posible desalineación entre vars UI y estado servicio si no se invoca refresh tras cada mutación.
2. Dominio: UI sugiere filtrado funcional pero servicio devuelve placeholder (riesgo de UX engañosa).
3. Thread update repo (`_on_update_repo`) toca UI vía `after`, correcto, pero lógica git en runtime sigue siendo operación sensible.
4. Cache por firma (`_rendered_stage_signatures`) puede ocultar cambios si firma no captura todo estado relevante.

## D. UX quality assessment
- **Consistencia:** visual y de tokens buena; lenguaje mixto técnico/operativo coherente.
- **Descubribilidad:** razonable para flujo lineal; action bar + panel auxiliar ayudan.
- **Escalabilidad técnica UX:** limitada por monolito HomePanel y ausencia de composición por feature.
- **Aptitud para workflows analíticos densos:** moderada; Matplotlib embebido sirve para MVP, pero faltan patrones de drill-down/linked brushing/persisted layouts.
- **¿Soporta una tab tipo Power BI?:** parcialmente. El contenedor actual no alcanza por sí solo para analítica densa sin modularizar estado/componentes.

## E. Variography tab fit analysis
### Dónde enchufar la futura tab
- Navegación ya existente en `_build_step_progress` y `_show_stage_view`.
- Implementar contenido real sustituyendo `_render_variography_view` + `_build_variography_actions_inline` + `_build_variography_controls`.

### Patrones reutilizables
- `DashboardGrid` para layout de gráficos variográficos.
- Snapshot/readiness desde `GeostatService` para contexto activo.
- `ActivityLogService` para trazabilidad de acciones variográficas.
- Estructura “Resumen ejecutivo + Detalle técnico” usada en EDA/Cutoffs/Espacial.

### Qué crear nuevo
- Panel de parámetros variográficos (lag, n_lags, azimut/dip/tolerancias, max distance, downsampling).
- Servicio de aplicación variográfica con validación y contratos tipados.
- Renderer específico variografía (experimental + eventualmente modelos teóricos).
- Persistencia de configuración/modelo variográfico.

## F. UI blockers
1. `HomePanel` demasiado acoplado para seguir creciendo sin degradación.
2. Estado duplicado entre UI vars y `workflow_state`.
3. Dominios deshabilitados pero UX expone controles que parecen activos.
4. Falta contrato formal de datos entre UI y dominio para variografía.
5. Pruebas UI centradas en estructura AST, no en comportamiento interactivo end-to-end.
