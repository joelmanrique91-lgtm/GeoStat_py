# CODEBASE AUTO-AUDIT (GeoStat_py)

## 1. Executive Summary
- **Qué es la aplicación:** una app desktop local en Python con **CustomTkinter + Matplotlib** para flujo secuencial geoestadístico: `Datos -> EDA -> Cutoffs -> Espacial -> Dominios -> Variografía` (entrypoint `app/main.py`, shell `app/ui/main_window.py`, panel único `app/ui/panels/home_panel.py`).
- **Madurez actual:** **prototipo funcional intermedio** en Datos/EDA/Cutoffs/Espacial; Dominios y Variografía están mayormente en placeholder.
- **Calidad arquitectónica global:** aceptable para MVP, pero con acoplamiento alto UI-servicio y estado mutable distribuido.
- **Top riesgos:**
  1. `HomePanel` monolítico concentra navegación, render, estado y callbacks (más de 2k líneas).
  2. Contratos de dominio/variografía inconsistentes: readiness dice “ready”, pero módulos están deshabilitados (`GeostatService.get_workflow_readiness`, `configure_domains`, `set_active_domain`, `_render_variography_view`).
  3. Variografía computacional existe (`compute_experimental_variogram`) pero no está integrada al servicio/UI.
  4. Estado analítico depende de mezcla de `StringVar/BooleanVar` + `workflow_state` + dataframe mutable.
  5. Falta capa de contratos explícitos (DTO/schema versionados) para futura paralelización FE/BE.
- **Top fortalezas:**
  1. Startup simple y claro (`app/main.py -> MainWindow -> HomePanel`).
  2. Servicios de preparación visual separados (`app/services/visualization_service.py`).
  3. Wrappers de render reutilizables (`DashboardGrid`, renderers 2D/EDA/3D interfaces).
  4. Logging de actividad por sesión (`ActivityLogService`, JSONL).
  5. Suite de tests relevante en contratos de servicio y regresiones UI por AST.

## 2. Repository Map
### Estructura relevante (top-level)
- `app/`: código de aplicación.
  - `app/main.py`: bootstrap.
  - `app/ui/`: shell y renderizado.
  - `app/services/`: lógica de aplicación/cómputo.
  - `app/models/`: estado/config.
  - `app/adapters/`: integración GeostatsPy.
  - `app/utils/paths.py`: paths globales.
- `tests/`: unit tests/regresiones (servicio + inspección AST UI).
- `scripts/`: launch/update runtime y fuera de GUI.
- `docs/`: auditorías y planes previos.
- `geostatspy/`: submódulo externo esperado.
- `data/`, `logs/`, `notebooks/`, `workflows/`: datos auxiliares/workflow docs.

### Áreas ambiguas o potencialmente “muertas”
- `Dominios`: UI visible, pero servicio devuelve “módulo deshabilitado” en métodos clave.
- `Variografía`: tab y textos existen, pero sin ejecución real en UI/servicio.
- `PyVistaSpatial3DRenderer`: diseñado para fallback permanente (siempre `is_available=False` por decisión de fase).

## 3. Runtime Architecture
### Startup real
1. `app/main.py::main()` crea `GeostatSpyAdapter`, `ActivityLogService`, `GeostatService`.
2. Se registra evento `app_started`.
3. Se instancia `MainWindow(service)`.
4. `MainWindow._build_layout()` monta `HomePanel` como único panel principal.
5. `MainWindow.run()` inicia `root.mainloop()`.

### Capas y límites
- **UI capa:** `HomePanel`, `DashboardGrid`, renderers matplotlib/3D.
- **Aplicación:** `GeostatService` (carga CSV, config de variables, cutoffs, preparación EDA/espacial, readiness).
- **Dominio/cómputo numérico:** funciones puras en `visualization_service.py` (`prepare_spatial_sections`, `prepare_spatial_3d_cloud`, `compute_swath_series`, `compute_experimental_variogram`).
- **Persistencia liviana:** logs JSONL y mutación en-memory de dataframe.
- **Integración externa:** `GeostatSpyAdapter` (import probing GeostatsPy).

### Dependencias de alto nivel
`HomePanel` -> `GeostatService` -> (`DatasetModel`, `VariableConfigModel`, `WorkflowStateModel`, `visualization_service`) + `ActivityLogService`.

## 4. GUI / UX Architecture
### Composición de pantallas/tabs
- Navegación por botones de etapa en `HomePanel._build_step_progress`.
- Vista activa renderizada por `_show_stage_view` con dispatch a:
  - `_render_eda_view`
  - `_render_cutoff_view`
  - `_render_spatial_view`
  - `_render_domains_view`
  - `_render_variography_view`
- Cada etapa además tiene “action bar” inline (`_render_stage_action_bar`) y panel auxiliar colapsable (`_render_control_sections`).

### Layout real
- Grid principal en `_build_layout`:
  - Header
  - Progress row
  - `content_panel` con KPIs + action bar + `view_body`
  - panel auxiliar opcional
  - log panel colapsable.

### Interacciones y actualización
- Patrones predominantes:
  - callbacks directos de botones/menus/switches (`_on_load_csv`, `_on_apply_config`, `_on_apply_cutoffs`, `_on_apply_dynamic_cutoff`, `_on_spatial_color_changed`, etc.).
  - refresco central `self._refresh_dashboard(reason=...)`.
  - invalidación manual por etapa (`_invalidate_stage_cache(...)`) y firmas en `_rendered_stage_signatures`.
  - debounce manual para preview cutoff (`after(80, ...)`) y resize (`DashboardGrid._on_parent_configure`).

### Dónde vive el estado
- **UI local (ad hoc/distribuido):** muchas `ctk.StringVar/BooleanVar/DoubleVar` en `HomePanel.__init__`.
- **Estado global operativo:** `GeostatService.workflow_state` (`WorkflowStateModel`).
- **Datos primarios:** `GeostatService.current_dataset.dataframe` mutable en memoria.
- **Conclusión:** estado **distribuido/ad hoc**, no centralizado por store único.

### Cómo se refrescan charts
- EDA: `GeostatService.prepare_univariate_data` + `MatplotlibEDARenderer.render`.
- Espacial 2D: `GeostatService.prepare_visual_data` + `MatplotlibSpatial2DRenderer.render`.
- Espacial 3D: `prepare_visual_3d_data` + renderer Matplotlib 3D (fallback desde PyVista).
- Cutoff preview: generado en UI (`_render_cutoff_preview_plots`) con datos de `prepare_dynamic_cutoff_preview`.

### Reactividad real
- No hay framework reactivo formal; la sincronización es **manual** (imperativa), basada en callbacks + refresh explícito + cache signatures.

### Reusabilidad para futura tab Variography
- Reusable: shell de etapa, action bar, `DashboardGrid`, patrón de renderer interface, métodos de servicio para snapshot/readiness.
- Limita: el patrón actual depende de gran cantidad de estado local y branching en una sola clase.

## 5. Current Variography Readiness
### Lo existente reutilizable
- Etapa visible `Variografía` ya existe en navegación y staging (`HomePanel`, `WORKFLOW_STEPS`).
- Primitive variográfica implementada en dominio: `compute_experimental_variogram` y dataclass `VariogramResult`.
- Infra de gráficas disponible (DashboardGrid + estilos + renderers).
- Snapshot/readiness de contexto analítico (`get_analysis_context_snapshot`, `get_workflow_readiness`).

### Lo faltante/crítico
- No hay método en `GeostatService` que exponga variograma experimental como caso de uso de aplicación.
- `_render_variography_view` es placeholder estático.
- No hay panel de parámetros variográficos reutilizable ya integrado.
- No existe contrato persistible de modelo variográfico (JSON schema/DTO versionado).
- Dominios deshabilitados reduce integración natural para variografía por dominio.

### Evaluación de host UX para nuevo diseño
- El host puede alojar la nueva vista sin romper navegación, pero la implementación segura requiere extraer lógica de `HomePanel` para evitar degradación adicional.

## 6. Data Flow Analysis
### Flujo 1: cambio de filtro/selector visual -> actualización UI
1. Usuario cambia color o modo espacial (`_on_spatial_color_changed` / `_on_spatial_mode_changed`).
2. HomePanel invalida cache etapa y llama `_refresh_dashboard`.
3. `_show_stage_view` reentra en `_render_spatial_view`.
4. `_render_spatial_2d_view` llama `service.prepare_visual_data(color_by=...)`.
5. Servicio resuelve contexto (`_resolve_spatial_visual_context` + snapshot/readiness), prepara bundle con `prepare_spatial_sections`.
6. Renderer 2D dibuja XY/XZ/YZ + ficha técnica.

### Flujo 2: edición de parámetros -> cómputo
1. Usuario mueve slider cutoff (`_on_slider_change`) -> debounce (`_schedule_cutoff_preview`).
2. `_refresh_cutoff_preview` genera firma y evita rerender redundante.
3. `_render_cutoff_preview_plots` llama `service.prepare_dynamic_cutoff_preview(target, mode, percent)`.
4. Servicio calcula cutoff, impacto, series derivadas (retained/truncated/capped, QQ inputs).
5. UI dibuja 4 subplots y actualiza labels de impacto/cutoff.

### Flujo 3: persistencia/log/publicación
1. Cada evento de usuario relevante llama `service.activity_log.log(...)` (e.g. `ui_trace`, `csv_load_started`, `cutoff_applied`, `spatial_2d_rendered`).
2. `ActivityLogService` escribe JSONL por sesión en `logs/session_*.jsonl`.
3. Export manual vía `_on_export_log -> service.export_activity_log -> ActivityLogService.export_log`.
4. No hay flujo de “publish model” (ausente).

## 7. Technical Debt and Risks
1. **God object UI:** `HomePanel` acumula layout, estado, interacción, lógica de render y trazas.
2. **Inconsistencia readiness vs implementación real:** Dominios/Variografía figuran listas pero operativamente deshabilitadas.
3. **Contratos implícitos:** payloads dict sin schema formal/versionado; alto riesgo de regresión silenciosa.
4. **Acoplamiento UI-servicio:** UI conoce múltiples detalles internos de `workflow_state` y del dataset.
5. **Persistencia limitada:** estado analítico no serializable/reanudable salvo logs.
6. **Variograma O(n²):** `compute_experimental_variogram` puede escalar mal sin indexado/vectorización.
7. **Cobertura UI incompleta:** tests UI son mayormente estructurales/AST; falta prueba interacción end-to-end.
8. **Fallback 3D rígido:** PyVista declarado pero no embebido; limita roadmap de visualización avanzada.

## 8. Reuse vs Redesign
### Reuse as-is
- `ActivityLogService`.
- `DatasetModel`, `VariableConfigModel`.
- `DashboardGrid` (con debounce resize).
- Renderers base interfaces (`app/ui/renderers/base.py`).

### Reuse with refactor
- `GeostatService` (extraer sub-servicios de dominio/variografía y contratos tipados).
- `HomePanel` (split por etapa + presenters/controllers).
- `WorkflowStateModel` (reducir estado duplicado con UI vars).
- `visualization_service.compute_experimental_variogram` (optimizar + integrar).

### Redesign required
- Dominio/variografía application contracts (DTO/schema versionado).
- Gestión de estado global para tab analítica avanzada.
- Flujo de persistencia de configuración/modelo (save/load/publish).

## 9. Recommended Implementation Strategy
### Estrategia mínima-riesgo (corto plazo)
1. Mantener shell actual de etapas.
2. Implementar `VariographyService` nuevo (application layer) consumido por `GeostatService`.
3. Crear `VariographyPanel`/renderer dedicado sin ampliar `HomePanel` en exceso (montaje desde dispatch por etapa).
4. Introducir contrato explícito `VariographyRequest/Response` (dataclasses + validación).
5. Añadir tests de contrato para variografía y flujo UI-Servicio mínimo.

### Estrategia ideal (largo plazo)
- Migrar a arquitectura por features:
  - `app/features/{data,eda,cutoffs,spatial,variography}`
  - panel por feature + estado desacoplado.
- Adoptar store de estado único (o view-model layer) para reducir sincronización manual.
- Persistencia de sesión analítica (json) con versionado.

### Opción incremental de migración
- Fase 1: introducir service y DTO variografía sin tocar etapas existentes.
- Fase 2: extraer paneles existentes (EDA/Cutoffs/Espacial) desde HomePanel a módulos separados.
- Fase 3: unificar state management y contracts de persistencia/publicación.

## 10. Readiness for Next Phase
- **Generación de tickets técnicos:** **READY WITH RISKS**.
- **Diseño arquitectura motor de variografía:** **READY WITH RISKS** (la base algorítmica existe, falta capa de aplicación).
- **Trabajo paralelo backend/frontend:** **parcialmente posible** si primero se congelan contratos de entrada/salida y estado.

### Respuestas explícitas requeridas
1. **Framework/paradigma UI:** CustomTkinter + Matplotlib embebido en Tk (`FigureCanvasTkAgg`), arquitectura desktop imperativa.
2. **Estado GUI:** distribuido/ad hoc entre `HomePanel` vars + `workflow_state` + dataframe.
3. **Render/update plots:** llamadas explícitas a servicio y renderers, con debounce/cache manual.
4. **Patrón de workflow tabulado:** sí, por botones de etapa y dispatcher `_show_stage_view`.
5. **Panels reutilizables de filtros/parámetros:** sí (action bar + panel auxiliar), pero aún no modularizados por feature.
6. **Capa de dominio separada o mezclada:** parcialmente separada; hay lógica de dominio en servicio/helpers, pero parte sigue mezclada en UI.
7. **Punto de inserción de motor variografía de menor riesgo:** nuevo servicio bajo `app/services` + nuevo renderer/panel enganchado en `_render_variography_view` y action bar variografía.
8. **Mayor riesgo arquitectónico para la nueva tab:** crecimiento del acoplamiento y complejidad en `HomePanel`/estado duplicado.
9. **¿Backend y frontend pueden ir paralelo ya?:** no plenamente; antes deben acordarse contratos variográficos y estados oficiales.
10. **Qué estabilizar antes de tickets:** contratos DTO, ownership de estado, estrategia de persistencia de sesión/modelo, límites HomePanel vs servicios.

## Veredicto global
**READY WITH RISKS**
