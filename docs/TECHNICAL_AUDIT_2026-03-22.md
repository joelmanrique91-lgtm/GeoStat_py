# Auditoría técnica profunda — GeoStat_py

Fecha: 2026-03-22  
Alcance: todo el código bajo `app/`, `tests/`, `scripts/`, `workflows/` y documentación técnica existente.

## A) Resumen ejecutivo

GeoStat_py es una aplicación desktop guiada por etapas (**Datos → EDA → Cutoffs → Espacial → Dominios**) con UI en CustomTkinter, cálculo de negocio en un servicio monolítico (`GeostatService`) y renderizado distribuido entre `HomePanel` + renderers Matplotlib (con fallback 3D). El sistema funciona y está testeado, pero presenta **concentración de complejidad** en dos archivos (`geostat_service.py`, `home_panel.py`) que actúan como *god objects* y elevan costo de cambio, riesgo de regresión y dificultad de observabilidad real de performance.

### Hallazgo principal

El problema no es una lógica de negocio incorrecta, sino **deuda estructural por crecimiento iterativo**: demasiada responsabilidad en capas “coordinadoras”, cierta duplicación de reglas de readiness/mensajes, y algunos elementos de over-engineering o no utilizados todavía (PyVista piloto siempre deshabilitado, tokens de tema sin uso).

---

## B) Qué hace realmente el sistema (arquitectura real)

## Flujo operativo real

1. `app.main` crea adapter + logger + service + `MainWindow` y arranca UI.
2. `MainWindow` aloja un único panel principal (`HomePanel`).
3. `HomePanel` concentra navegación, estado de widgets, eventos de usuario, refresco visual y orquestación de acciones.
4. `GeostatService` concentra reglas de dominio, EDA, cutoffs, preparación espacial 2D/3D, readiness, snapshot de contexto, logging y operación de actualización de repo.
5. Renderers dibujan EDA/espacial sobre payloads que entrega el service.

## Arquitectura efectiva por capas

- **UI/orquestación**: `app/ui/panels/home_panel.py` (muy alto acoplamiento).
- **Lógica de negocio**: `app/services/geostat_service.py` (núcleo funcional, muy grande).
- **Modelos de estado**: `WorkflowStateModel`, `VariableConfigModel`, `DatasetModel`.
- **Preparación visual “pura”**: `visualization_service.py` (más cohesionada).
- **Infra/adaptadores**: `ActivityLogService`, `GeostatSpyAdapter`, utilidades de paths.

---

## C) Lista priorizada de problemas (impacto vs esfuerzo)

## P0 — Alta prioridad

1. **God Service (`GeostatService`)**
   - 1737 LOC, 74 funciones; método crítico `prepare_univariate_data` de 205 líneas.
   - Mezcla IO CSV, reglas de negocio, readiness, logs, estado mutable y operaciones de git.
   - Impacto: alto riesgo de regresión, tests más costosos, onboarding lento.

2. **God UI (`HomePanel`)**
   - 1852 LOC, 93 funciones; constructor con gran cantidad de estado UI mutable.
   - Orquesta navegación, dibuja vistas, calcula mensajes diagnósticos y ejecuta acciones de servicio.
   - Impacto: cambios visuales simples requieren tocar lógica extensa.

3. **Acoplamiento fuerte UI ↔ Service por contratos dict no tipados**
   - `HomePanel` depende de muchas claves literales de dicts (`snapshot`, `cutoff_state`, payloads EDA).
   - Impacto: errores silenciosos por claves faltantes o cambios de contrato.

## P1 — Prioridad media

4. **Duplicación de reglas/mensajes de readiness y bloqueo**
   - Reglas de estado repartidas entre `_build_active_step_hint`, `get_workflow_readiness`, validaciones de métodos y textos hardcoded.
   - Impacto: inconsistencias UX/lógica y mantenimiento costoso.

5. **Over-engineering parcial en renderer 3D PyVista**
   - Existe adapter PyVista pero `is_available()` retorna `False` incluso si importa dependencias (bloqueo deliberado por “fase piloto”).
   - Impacto: complejidad adicional en selección/fallback sin valor funcional actual.

6. **Código potencialmente muerto / no usado**
   - Tokens de tema no referenciados (`TEXT_SOFT`, `GRID_COLOR`, `get_categorical_cmap`).
   - Impacto: ruido cognitivo bajo, pero fácil de limpiar.

## P2 — Prioridad baja

7. **Cuello de botella potencial en variograma experimental**
   - Implementación O(n²) por doble loop de pares, mitigada parcialmente con downsampling.
   - Impacto: datasets medianos/grandes pueden degradar rápidamente.

8. **Logging de alta granularidad en rutas calientes**
   - `prepare_univariate_data` registra múltiples eventos por ejecución.
   - Impacto: overhead de IO en disco y logs muy verbosos en uso intensivo.

---

## D) Detección explícita de problemas

## 1) Código muerto o de bajo uso

- **Tokens tema sin uso aparente**: `TEXT_SOFT`, `GRID_COLOR`, `get_categorical_cmap`.
- **`PyVistaSpatial3DRenderer.render` inalcanzable en operación normal** porque `is_available()` termina devolviendo `False` por diseño piloto.

## 2) Código duplicado

- Duplicación de patrones de validación “no hay dataset/configuración…” en múltiples métodos del service.
- Múltiples ramas de fallback de columnas/target/dominio con lógica similar.
- En UI, bloques repetidos de “wrapper + labels resumen + try/except + fallback label” en vistas EDA/Espacial/3D.

## 3) Complejidad innecesaria / over-engineering

- `HomePanel` mantiene gran número de `StringVar/BooleanVar` y estado derivado local + estado derivado de service.
- Múltiples métodos mezclan presentación, decisiones de dominio y manejo de errores de negocio.
- Modo PyVista agregando capa de abstracción que aún no habilita comportamiento real.

## 4) Uso de estructuras de datos mejorable

- Contratos de negocio complejos basados en `dict[str, object]` en lugar de dataclasses/TypedDict para payloads críticos de EDA/contexto.
- Historiales/estados en `WorkflowStateModel` como estructuras abiertas pueden crecer sin control ni validación de esquema.

## 5) Posibles cuellos de botella

- `compute_experimental_variogram` (O(n²) en pares) con potencial de tiempos altos.
- Repetición de conversiones `to_numeric`, `dropna`, `groupby`, `value_counts` entre llamadas de refresco.
- Refrescos de dashboard que pueden recalcular payloads completos con alta frecuencia ante eventos UI.

---

## E) Métricas estimadas

## Complejidad por módulo (estimada)

- **Muy alta**: `app/services/geostat_service.py`, `app/ui/panels/home_panel.py`.
- **Media**: `app/services/visualization_service.py`, `app/ui/renderers/mpl_eda_renderer.py`, `app/ui/panels/spatial_3d_view.py`.
- **Baja**: modelos, adapter, paths, main window, servicios pequeños.

## Señales cuantitativas observadas

- `geostat_service.py`: 1737 líneas, 74 funciones, función más larga 205 líneas.
- `home_panel.py`: 1852 líneas, 93 funciones, función más larga 108 líneas.
- `visualization_service.py`: 256 líneas, 5 funciones, función más larga 63 líneas.

## Acoplamiento

- **Alto** entre `HomePanel` y `GeostatService` (acceso constante a estado interno y contratos dict).
- **Medio** entre service y pandas/matplotlib por preparación de payloads.
- **Bajo** en modelos y utilidades.

## Cohesión

- **Baja-media** en `GeostatService` (demasiadas responsabilidades heterogéneas).
- **Baja-media** en `HomePanel` (UI + orquestación + lógica condicional extensa).
- **Alta** en `DatasetModel`, `ActivityLogService`, `DashboardGrid`, renderers individuales.

---

## F) Plan de refactor en fases (sin romper contratos)

## Fase 1 — Limpieza segura (quick wins)

1. Eliminar tokens/funciones no usadas de `theme.py`.
2. Centralizar strings de errores comunes en constantes compartidas.
3. Introducir helpers internos para validación repetida (dataset/config, target válido, dominio válido).
4. Reducir logging redundante en rutas de alto uso (mantener eventos clave de trazabilidad).

**Riesgo**: bajo.  
**Validación**: tests existentes + smoke manual en flujo Datos→EDA→Espacial.

## Fase 2 — Simplificación estructural

1. Particionar `GeostatService` en componentes:
   - `DatasetService` (carga/config/autodetección)
   - `CutoffService` (manual + dinámico)
   - `DomainService` (definiciones, filtros, estadísticas)
   - `ReadinessService` (snapshot/readiness)
2. Mantener `GeostatService` como façade para no romper API pública.
3. Extraer builders de payload EDA a módulo dedicado (`eda_payload_builder.py`).
4. En UI, extraer controladores por etapa desde `HomePanel`.

**Riesgo**: medio (movimiento grande de código).  
**Mitigación**: conservar firmas públicas actuales y añadir tests de contrato por método façade.

## Fase 3 — Performance

1. Cachear resultados derivados por firma de contexto (dataset id + target + filtros + cutoff).
2. Evitar recomputar `to_numeric`/`groupby` cuando snapshot no cambió.
3. Reemplazar variograma O(n²) por versión vectorizada o muestreo por pares controlado.
4. Desacoplar logging sync en caliente (buffer/cola opcional).

**Riesgo**: medio-alto si se altera orden de cálculos.  
**Mitigación**: pruebas de equivalencia numérica y tolerancias explícitas.

## Fase 4 — Mejoras opcionales

1. Definir `TypedDict`/dataclasses para snapshot, readiness y payloads EDA.
2. Habilitar feature flag real para backend 3D (mantener fallback estable).
3. Introducir métricas runtime (tiempos por etapa, conteo de re-render).

**Riesgo**: bajo/medio según alcance.

---

## G) Propuestas concretas (problema → solución)

## 1) God Service

**Problema**: una clase concentra demasiadas capacidades y estado mutable.  
**Solución**: extraer servicios internos preservando fachada.

Pseudocódigo:

```python
class GeostatService:
    def __init__(...):
        self.dataset_ops = DatasetService(...)
        self.cutoff_ops = CutoffService(...)
        self.domain_ops = DomainService(...)
        self.readiness_ops = ReadinessService(...)

    # API pública intacta
    def load_csv(self, file_path):
        return self.dataset_ops.load_csv(file_path)
```

## 2) Contratos dict frágiles

**Problema**: claves string dispersas y poco seguras.  
**Solución**: introducir tipos estructurados sin cambiar salida externa.

Pseudocódigo:

```python
class AnalysisSnapshot(TypedDict):
    readiness: str
    blocking_reason: str
    resolved_target_column: str
    active_domain_column: str
```

## 3) Repetición de validaciones

**Problema**: muchos métodos repiten chequeos de dataset/config/columnas.  
**Solución**: helper central `_require_dataset_and_config()` + `_require_target()`.

## 4) Variograma O(n²)

**Problema**: costo cuadrático en pares.  
**Solución**: muestreo de pares + vectorización (NumPy) con límites por budget.

## 5) UI monolítica

**Problema**: `HomePanel` mezcla demasiadas responsabilidades.  
**Solución**: controllers por etapa (`DataStageController`, `EDAStageController`, etc.) y `HomePanel` como ensamblador.

---

## H) Reglas de refactor propuestas

1. No romper APIs de `GeostatService` usadas por tests/UI.
2. No cambiar nombres/estructura de retorno hasta introducir capa de compatibilidad.
3. Mantener mensajes existentes cuando son parte del flujo UX validado.
4. Introducir cambios por feature flag cuando impacten render/performances.
5. Ejecutar suite completa en cada fase.

---

## I) Riesgos y mitigación

- **Riesgo de regresión funcional** al mover lógica entre módulos.  
  Mitigación: snapshot tests de contratos + golden outputs de payloads.
- **Riesgo de drift UI** por separación de controllers.  
  Mitigación: tests por etapa + checklist visual manual.
- **Riesgo de performance “falsa mejora”**.  
  Mitigación: baseline de tiempos antes/después y presupuesto de latencia por vista.

---

## J) Recomendación de ejecución (impacto/efort)

1. Semana 1: Fase 1 completa (quick wins + reducción ruido + helpers).  
2. Semana 2-3: Fase 2 en slices pequeños preservando façade.  
3. Semana 4: Fase 3 sobre variograma + caching selectivo.  
4. Semana 5+: Fase 4 opcional según roadmap (tipado fuerte + backend 3D real).

Resultado esperado: menor complejidad accidental, mayor mantenibilidad y mejora de latencia percibida sin romper contratos existentes.
