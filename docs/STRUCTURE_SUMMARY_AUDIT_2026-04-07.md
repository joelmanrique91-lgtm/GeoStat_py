# Auditoría técnica de estructura y summary vigente (GeoStat_py)

> Estado documental: **VIGENTE (FUENTE CANÓNICA)**
> Fecha de corte: **2026-04-07**
> Propósito: referencia única del estado actual as-built para onboarding, auditoría y toma de decisiones.

Fecha: 2026-04-07

## Convención de vigencia usada
- **VIGENTE**: describe estado actual verificable del repo y se usa como fuente primaria.
- **HISTÓRICO**: documento válido como trazabilidad, no como fuente primaria del estado actual.

## Matriz breve de features (estado real)
| Área | Estado | Evidencia principal |
|---|---|---|
| Datos/EDA/Cutoffs/Espacial | Implementado | `app/services/geostat_service.py`, `app/ui/panels/home_panel.py` |
| Dominios | Parcial (módulo deshabilitado en operaciones clave) | `is_domains_module_enabled=False`, `configure_domains/apply_domain_definition` retornan mensaje de módulo deshabilitado |
| Variografía experimental + modelado inicial | Implementado (slice funcional activo) | `compute_experimental_variography`, `VariographyApplicationService`, `VariographyController`, `VariographyStageView`, tests variográficos |
| Backend 3D dedicado | Parcial/dinámico (pyvista o plotly según disponibilidad) | `PyVistaSpatial3DRenderer._resolve_backend/is_available` |

## 1) Resumen ejecutivo breve

### Distancia de la estructura actual vs estándar “bueno”
La estructura está **a distancia media** de un estándar bueno: existe separación base por capas (`app/models`, `app/services`, `app/ui`, `app/adapters`), pero persiste un nodo de complejidad alta en `HomePanel` (2547 LOC) y un service principal aún amplio (`GeostatService`, 1117 LOC), lo que reduce mantenibilidad y auditabilidad fina.

### Distancia del summary actual vs summary realmente útil
El summary más parecido al documento de síntesis (`docs/CODEBASE_AUTOAUDIT.md`) quedó **desalineado** en puntos críticos: afirma que Variografía es mayormente placeholder, pero hoy hay servicio, controlador, vista de etapa y tests activos para cálculo experimental/modelado básico. También indica que PyVista está “siempre” deshabilitado, mientras que el renderer actual habilita backend dinámico `pyvista` o `plotly` según disponibilidad.

### Riesgos principales de seguir igual
1. Decisiones técnicas/roadmap basadas en diagnóstico viejo (riesgo de priorizar mal).
2. Overhead de onboarding y auditoría por contradicción entre documentación y código real.
3. Riesgo de regresión por concentración de lógica en `HomePanel` y contratos dict amplios.

---

## 2) Mapa actual del proyecto

### Módulos/carpetas relevantes y propósito aparente
- `app/main.py`: bootstrap de app desktop.
- `app/ui/`: shell (`main_window.py`), panel principal (`home_panel.py`), vistas de etapa (`panels/stages`), renderers.
- `app/services/`: capa de aplicación y servicios auxiliares (dataset/contexto, estado operacional, cutoff, variografía, persistencia de escena, etc.).
- `app/models/`: contratos/estado operativo, espacial y variografía.
- `tests/`: contratos de servicios, smoke de integración y hardening UI.
- `docs/`: auditorías, planes, reportes y guías.

### Relación entre componentes
`app.main -> MainWindow -> HomePanel`, y desde UI se delega en `GeostatService` + controladores especializados (`SpatialViewerController`, `VariographyController`). En variografía, el flujo ya es `HomePanel -> VariographyStageView -> VariographyController -> GeostatService.compute_experimental_variography -> VariographyApplicationService`.

---

## 3) Auditoría de estructura

### Fortalezas
1. **Capas visibles y reconocibles**: organización por `models/services/ui/adapters` consistente con proyecto desktop por responsabilidades.
2. **Slice funcional de variografía ya real**: existen servicio de aplicación, controlador y vista dedicada; no es solo placeholder.
3. **Cobertura de tests variográficos**: hay pruebas de contrato y smoke integración del flujo de cálculo.
4. **Trazabilidad operativa**: eventos de actividad y estado del workflow en servicios/modelos dedicados.

### Debilidades
1. **Concentración de complejidad UI**: `HomePanel` continúa como macro-componente de orquestación + estado + render + callbacks.
2. **Service núcleo aún grande**: `GeostatService` conserva alta superficie funcional.
3. **Contratos heterogéneos por dict** en flujos UI-servicio (riesgo de drift de claves/campos).
4. **Documentación de arquitectura desactualizada** frente al estado implementado.

### Inconsistencias observables
1. Summary vigente de síntesis describe variografía como placeholder, pero código y tests muestran feature activa.
2. Summary indica PyVista permanentemente no disponible, pero renderer usa detección dinámica y fallback pyvista/plotly.
3. README raíz presenta estructura con carpetas opcionales (`data`, `notebooks`, `logs`, `geostatspy`) que no están en el árbol actual del repo versionado, lo cual mezcla estructura conceptual con estructura real observada.

### Deuda técnica observable
- Reducir tamaño/responsabilidad de `HomePanel`.
- Reducir área de `GeostatService` moviendo más capacidades a servicios especializados (algunos ya existen, pero no completa la extracción).
- Formalizar contratos tipados de intercambio UI-servicio para reducir ambigüedad.
- Consolidar un único “summary fuente de verdad” y retirar/etiquetar snapshots históricos que ya no representan el presente.

---

## 4) Auditoría del summary actual

## Documento auditado como “summary actual”
`docs/CODEBASE_AUTOAUDIT.md` (por contenido de síntesis ejecutiva + mapa + veredicto global).

### Qué comunica bien
- Señala adecuadamente la existencia de deuda estructural en `HomePanel`.
- Explicita riesgos de acoplamiento y necesidad de contratos más claros.
- Mantiene formato útil (Executive Summary + mapa + estrategia).

### Qué comunica mal
- Estado de variografía: lo presenta como no integrado, pero hoy sí existe integración funcional.
- Estado backend 3D: mantiene narrativa de indisponibilidad rígida, ya no exacta.

### Qué falta
- Estado “as built” actualizado de componentes nuevos (`variography_application_service`, `variography_controller`, `variography_stage_view`, tests dedicados).
- Distinción explícita entre hallazgos históricos vs estado actual.
- Señales cuantitativas actualizadas (line counts actuales, cobertura por área, deuda priorizada con fecha vigente).

### Qué sobra / genera ruido
- Secciones que mezclan recomendaciones futuras con afirmaciones de estado que ya cambiaron.
- Frases categóricas (“placeholder”, “no integrado”) sin fecha de validez ni condición.

### Por qué no alcanza hoy
Porque puede guiar decisiones de arquitectura con supuestos vencidos. Como documento histórico sirve; como summary operativo actual para onboarding/decisión, no.

---

## 5) Gap analysis (estado actual vs estándar esperado)

| Aspecto | Estado actual observado | Estado deseable (estándar bueno) | Desvío | Impacto | Recomendación puntual |
|---|---|---|---|---|---|
| Fuente única de síntesis | Hay múltiples auditorías; el summary de síntesis principal está parcialmente desactualizado | Un summary canónico vigente, versionado por fecha y con “as-built” verificable | Alto | Alto | Declarar un “CURRENT_SUMMARY.md” (o equivalente) y mover el resto a histórico explícito |
| Alineación summary-código | Variografía/3D reportados de forma no fiel al estado real | Correspondencia 1:1 con módulos y tests vigentes | Alto | Alto | Actualizar resumen con evidencia de archivos y tests actuales |
| Claridad estructural | Capas claras pero con mega-módulos centrales | Capas + componentes acotados por feature/etapa | Medio | Alto | Plan de extracción incremental de `HomePanel` y reducción de fachada `GeostatService` |
| Trazabilidad técnica | Existe logging y tests; falta mapa de contratos estable | Contratos explícitos, tipados y documentados | Medio | Medio/Alto | Definir contratos mínimos para payloads críticos UI-servicio |
| Mantenibilidad | Cambios de UI pueden tocar demasiado contexto | Cambios localizados por etapa sin efectos colaterales amplios | Medio/Alto | Alto | Seguir extracción de stage views/controllers y reducir estado distribuido |
| Reducción de ambigüedad | README mezcla estructura real con opcional conceptual | Diferenciar “árbol real” vs “directorios opcionales” | Medio | Medio | Ajustar README con sección “estructura versionada actual” y “estructura opcional local” |
| Utilidad para onboarding | Requiere reconciliar docs contradictorios | Documento de entrada único + enlaces secundarios por tema | Alto | Alto | Reescribir índice de docs con semáforo de vigencia (vigente/histórico/deprecado) |

---

## 6) Ranking de criticidad

### Crítico
1. Desalineación entre summary de síntesis y código real en capacidades variografía/3D.
2. Ausencia de una fuente única de verdad documental para estado actual.

### Importante
1. Complejidad y tamaño de `HomePanel`.
2. Superficie aún amplia de `GeostatService`.
3. Contratos dict poco tipados en integración UI-servicio.

### Secundario
1. README con mezcla de árbol real vs opcional local.
2. Consolidación de nomenclatura y fechas de auditorías históricas.

---

## 7) Definición de “summary bueno” (estructura objetivo)

Orden sugerido y contenido mínimo:

1. **Executive status (1 página)**
   - objetivo del producto;
   - estado funcional por etapa;
   - riesgos top 3;
   - veredicto de readiness.
2. **As-built architecture map**
   - entrypoints;
   - módulos por capa;
   - diagrama textual de flujo de datos/calls.
3. **Feature matrix (estado real)**
   - por etapa: implemented / partial / disabled;
   - evidencia de archivo + tests asociados.
4. **Technical debt register (priorizado)**
   - deuda, impacto, probabilidad, owner, próximo paso.
5. **Contracts and invariants**
   - payloads críticos, supuestos, validaciones y límites.
6. **Operational quality**
   - tests existentes por dominio;
   - brechas de cobertura;
   - riesgos de regresión.
7. **Roadmap incremental (30-60-90 días)**
   - quick wins;
   - cambios estructurales;
   - criterios de done/rollback.
8. **Evidence appendix**
   - lista de archivos inspeccionados;
   - comandos usados;
   - fecha de corte.

---

## 8) Plan de mejora incremental (bajo riesgo)

### Quick wins (1-3 días)
1. Marcar `docs/CODEBASE_AUTOAUDIT.md` como “histórico” o actualizarlo a estado 2026-04-07.
2. Crear documento canónico único de estado actual (este audit puede ser base).
3. Ajustar README para separar estructura real del repositorio vs estructura opcional local.

### Cambios importantes (1-2 semanas)
4. Definir contratos tipados mínimos en flujos de variografía y espacial.
5. Extraer más responsabilidades de `HomePanel` por etapa (sin romper comportamiento).
6. Reducir funciones de coordinación de `GeostatService` que hoy delegan parcialmente.

### Cambios más profundos (2-6 semanas)
7. Consolidar arquitectura por feature (etapas) con ownership claro.
8. Establecer pipeline de documentación viva: cada PR que cambia arquitectura actualiza summary canónico y su changelog.

---

## 9) Evidencia concreta

### Archivos inspeccionados
- `README.md`
- `docs/README.md`
- `docs/CODEBASE_AUTOAUDIT.md`
- `docs/PROJECT_AUDIT.md`
- `app/main.py`
- `app/services/geostat_service.py`
- `app/services/variography_application_service.py`
- `app/ui/panels/home_panel.py`
- `app/ui/controllers/variography_controller.py`
- `app/ui/panels/stages/variography_stage_view.py`
- `app/ui/renderers/pyvista_spatial3d_renderer.py`
- `tests/test_variography_service.py`
- `tests/test_variography_integration_smoke.py`

### Comandos usados
- `rg --files`
- `sed -n '1,220p' README.md`
- `sed -n '1,260p' docs/CODEBASE_AUTOAUDIT.md`
- `sed -n '1,260p' docs/PROJECT_AUDIT.md`
- `sed -n '1,260p' app/services/geostat_service.py`
- `sed -n '1,260p' app/ui/panels/home_panel.py`
- `sed -n '1,260p' app/services/variography_application_service.py`
- `sed -n '1,260p' app/ui/controllers/variography_controller.py`
- `sed -n '1,260p' app/ui/panels/stages/variography_stage_view.py`
- `sed -n '1,220p' app/ui/renderers/pyvista_spatial3d_renderer.py`
- `sed -n '1,260p' tests/test_variography_service.py`
- `sed -n '1,220p' tests/test_variography_integration_smoke.py`
- `rg -n "..." ...`
- `wc -l ...`

### Evidencia puntual de contradicciones
1. `CODEBASE_AUTOAUDIT` reporta variografía mayormente placeholder, pero existen `compute_experimental_variography`, `VariographyApplicationService`, `VariographyController`, `VariographyStageView` y tests dedicados.
2. `CODEBASE_AUTOAUDIT` reporta fallback PyVista rígido; el renderer actual detecta backend dinámicamente (`pyvista`/`plotly`) y expone disponibilidad real.
3. `docs/README.md` marca documentos “vigentes”, pero dentro de ese conjunto conviven piezas con distinto nivel de actualidad; falta semáforo de vigencia por fecha/alcance.

---

## Veredicto final
El proyecto **no está lejos** de una base estructural buena (arquitectura por capas y tests relevantes), pero sí está **lejos de un summary “bueno y confiable hoy”** porque la síntesis principal no refleja completamente el estado implementado actual. La brecha prioritaria no es reescribir el sistema, sino **reconstruir trazabilidad documental confiable + cerrar focos de complejidad estructural conocidos**.
