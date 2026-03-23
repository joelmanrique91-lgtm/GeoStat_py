# Especificación funcional y visual — Pestaña **06 Variografía** (GeoStat Py)

## 1) Objetivo

Definir una pestaña de variografía con enfoque técnico de geoestadística aplicada para:

- diagnosticar continuidad espacial;
- identificar y modelar anisotropía;
- ajustar modelos variográficos univariados y multivariables;
- validar consistencia matemática para kriging/cokriging;
- asegurar trazabilidad reproducible (auditoría técnica).

La pestaña **no** es un dashboard genérico: es un módulo de ingeniería geoestadística con reglas duras de cómputo y publicación.

---

## 2) Alcance funcional

### 2.1 Modos de trabajo

1. **Modo A — Exploración univariable**
   - mapa variográfico;
   - variogramas experimentales omni y direccionales;
   - identificación de anisotropía;
   - ajuste de modelo directo.

2. **Modo B — Validación geométrica**
   - estabilidad por lag/tolerancias/npairs;
   - comparación por dominio/subdominio/litología/fase.

3. **Modo C — Modelamiento multivariable**
   - directos y cruzados experimentales;
   - LMC con estructuras compartidas;
   - validación PSD por estructura.

4. **Modo D — Preparación para estimación**
   - bloqueo por invalidaciones;
   - versionado y publicación a kriging/cokriging;
   - snapshot completo de configuración y resultados.

---

## 3) Diseño visual y UX

### 3.1 Dirección de arte

- Estética oscura técnica (minería/geoestadística), no corporativa.
- Prioridad visual: curvas, mapa variográfico, npairs y estados de validez.
- Bajo ruido y alta legibilidad.

### 3.2 Paleta (tokens visuales)

| Token | Uso | Valor sugerido |
|---|---|---|
| `bg.base` | fondo principal | azul petróleo/grafito oscuro |
| `bg.panel` | paneles | gris azulado oscuro |
| `accent.active` | selección activa | azul eléctrico tenue |
| `series.experimental` | puntos experimentales | gris claro / blanco azulado |
| `series.model` | curva modelo | ámbar o cian suave |
| `series.major` | dirección mayor | verde azulado |
| `series.minor` | dirección menor | violeta suave |
| `series.vertical` | dirección vertical | naranja tenue |
| `state.warning` | advertencias | amarillo |
| `state.error` | errores/invalidación | rojo suave |

### 3.3 Reglas UX globales

- El número de pares por lag (`npairs`) debe ser visible en la misma vista del variograma.
- Todo warning crítico debe mostrarse en UI y persistirse en log técnico.
- Toda acción que invalide resultados debe marcar estado `dirty` y bloquear publicación hasta recálculo.

---

## 4) Layout de la pestaña

### 4.1 Franjas funcionales

1. **Franja 1 — Encabezado contextual**
   - dataset, soporte, compuesto, dominio/filtros;
   - variable primaria/secundaria;
   - modo uni/multi;
   - estado de modelo (`sin_calcular`, `experimental_ok`, `preliminar`, `validado`, `publicado`).

2. **Franja 2 — Barra de filtros y parámetros**
   - selectores + controles de cálculo + acciones (`Calcular`, `Autoajuste`, `Reset`, `Guardar versión`).

3. **Franja 3 — KPI cards**
   - `n_valid`, `n_pairs_total`, `lag_distance`, `n_lags`, `max_distance`;
   - `nugget_pct`, `sill_total`, `range_major/minor/vertical`, `anis_ratio`;
   - `fit_score`, `math_status`.

4. **Franja 4 — Zona analítica**
   - **Panel A**: mapa variográfico / rosa direccional.
   - **Panel B**: variograma experimental + modelo + barras `npairs`.
   - **Panel C**: tabla de estructuras editable.
   - **Panel D**: diagnóstico (residuales, calidad de lags, PSD/eigenvalues, log técnico).

5. **Franja 5 — Pie técnico colapsable**
   - eventos, warnings, snapshots de parámetros y cambios de versión.

### 4.2 Distribución recomendada

- Izquierda 25%: controles.
- Centro 50%: mapa variográfico (arriba) + variograma activo (abajo).
- Derecha 25%: KPIs + estructuras + validación.
- Inferior: log/versiones.

---

## 5) Geometric Conventions (Non-Ambiguous)

Estas convenciones son obligatorias en frontend, backend y exportaciones.

### 5.1 Sistema de coordenadas

- `X = Easting`
- `Y = Northing`
- `Z = Elevation` con convención **positiva hacia arriba**.

> Si el dataset de entrada usa `Z` positiva hacia abajo, se debe convertir internamente antes de calcular direcciones y distancias; guardar bandera `z_inverted=true` en sesión.

### 5.2 Azimut

- Origen: **Norte geográfico (eje +Y)**.
- Sentido: **horario**.
- Rango: `[0°, 360°)`.
- Ejemplos: 0°=N, 90°=E, 180°=S, 270°=W.

### 5.3 Dip

- Definido respecto al plano horizontal.
- Convención: **positivo hacia abajo**.
- Rango: `[-90°, +90°]` (0° horizontal; +90° vertical descendente).

### 5.4 Plunge/Rake

- En esta versión se utiliza **plunge** únicamente para describir eje principal 3D.
- `rake` no se usa y debe ocultarse para evitar ambigüedad.
- Rango plunge: `[-90°, +90°]` con misma convención de signo que dip.

### 5.5 Elipsoide de anisotropía y distancia transformada

Para una estructura con rangos `a_major`, `a_minor`, `a_vertical`, se define:

1. vector de separación: `h = x_j - x_i`
2. rotación al sistema local de anisotropía: `h' = R(azimuth,dip,plunge) * h`
3. distancia reducida:

\[
r = \sqrt{\left(\frac{h'_1}{a_{major}}\right)^2 + \left(\frac{h'_2}{a_{minor}}\right)^2 + \left(\frac{h'_3}{a_{vertical}}\right)^2}
\]

4. la función estructural se evalúa en `r` (o en `h_eq = r * a_major`, pero debe ser consistente en todo el motor).

### 5.6 Restricción de orden de rangos

Debe cumplirse siempre:

\[
a_{major} \ge a_{minor} \ge a_{vertical} > 0
\]

Si el usuario ingresa valores fuera de orden, el sistema debe:

- bloquear guardado si `strict_mode=true`; o
- reordenar automáticamente y notificar en log si `strict_mode=false`.

---

## 6) Componentes y contratos UI

### 6.1 Selectores principales

- `dropdown_variable_principal`
- `toggle_multivariable`
- `dropdown_variable_secundaria` (solo cuando `toggle_multivariable=true`)

**Reglas duras**

- `variable_secundaria != variable_principal`
- si heterotopía total para par `(i,j)`, deshabilitar cruzado experimental y marcar `hard_blocker` para publicación multivariable.

### 6.2 Selector geológico/filtros

- `dominio`, `subdominio`, `litologia`, `alteracion`, `fase_mineral`, `campania`.

Todo cambio invalida cache de pares y resultados experimentales.

### 6.3 Parámetros de cálculo

- `lag_distance`, `n_lags`, `lag_tolerance`, `max_distance`
- `azimuth`, `dip`, `plunge`
- `ang_tol_h`, `ang_tol_v`
- `band_width`, `band_height`
- `estimator`

Valores por defecto:

- `max_distance = 0.5 * max_sample_separation`
- `n_lags = 16`
- `lag_distance = max_distance / n_lags`
- `lag_tolerance = 0.5 * lag_distance`

### 6.4 Tipo de variograma

- `semivariogram` (default), `covariance`, `correlogram`, `madogram`, `indicator`, `relative`.

### 6.5 Opciones robustas

- `estimator = classical | cressie_hawkins`
- `remove_pair_outliers`
- `standardize_by_variance`
- `weight_by_npairs`

### 6.6 Acciones de modelamiento

- `add_structure`, `delete_structure`, `clone_structure`
- `auto_fit`
- `lock_shared_geometry`, `lock_sills`
- `fit_sills_only`, `fit_ranges_only`, `full_fit`
- `copy_geometry_to_all`

### 6.7 Publicación

- `save_draft`, `mark_validated`, `publish_kriging`, `publish_cokriging`
- `export_json`, `export_yaml`, `export_pdf`

---

## 7) Pair Selection Rules (N(h))

La definición de pares es obligatoria y única.

### 7.1 Definiciones

Para cada lag `k` con centro `h_k`:

- vector separación: `u_ij = x_j - x_i`
- distancia euclidiana: `d_ij = ||u_ij||`
- vector unitario de dirección objetivo `v_dir` (según azimuth/dip)

### 7.2 Condiciones de inclusión

Un par `(i,j)` pertenece a `N(h_k)` si y solo si cumple **todas**:

1. **Distancia**
\[
|d_{ij} - h_k| \le lag\_tolerance
\]

2. **Ángulo horizontal/vertical**

Sea `theta_h` y `theta_v` la desviación respecto a `v_dir` en proyecciones H y V.

\[
|\theta_h| \le ang\_tol_h \quad \land \quad |\theta_v| \le ang\_tol_v
\]

3. **Bandwidth / Bandheight**

- distancia ortogonal horizontal al eje direccional `<= band_width`
- distancia ortogonal vertical al eje direccional `<= band_height`

4. **Tolerancia vertical explícita (opcional)**

- si `vertical_tolerance` está definido, además debe cumplirse:
  `|Δz_ij - h_k * sin(dip)| <= vertical_tolerance`.
- si `vertical_tolerance=null`, la restricción vertical queda completamente representada por `ang_tol_v` y `band_height`.

5. **Cutoffs globales**

\[
min\_distance \le d_{ij} \le max\_distance
\]

por defecto `min_distance = 0` y `max_distance = 0.5 * max_sample_separation`.

### 7.3 Caso omnidireccional

- No aplica filtro de azimut/dip.
- Sí aplican `lag_tolerance`, `min/max_distance`.
- `band_width` y `band_height` se ignoran explícitamente (`null` en metadatos).

### 7.4 Binning y solapamiento

- Bins son **centrados** en `h_k = k * lag_distance`, `k=1..n_lags`.
- Tolerancia es simétrica (`± lag_tolerance`).
- Si un par cae en más de un bin por solapamiento:
  - modo por defecto: `unique_nearest_bin` (asignar al bin con menor `|d_ij-h_k|`);
  - modo alterno opcional: `allow_overlap=true` (duplicación explícita, no recomendado para fitting).

---

## 8) Lags, calidad y reglas de uso en ajuste

### 8.1 Definiciones

- `lag_distance`: separación entre centros de bins.
- `lag_tolerance`: semiancho del bin.
- `n_lags`: número de bins.
- `max_distance`: cutoff superior de pares.

## Data Quality Rules

Aplican por lag `k` y son obligatorias para visualización, ajuste y publicación.

### 8.2 Umbrales de calidad por lag

Por lag `k`:

- `npairs_k < 10` → `excluded_from_fit=true` (duro).
- `10 <= npairs_k < 30` → warning `low_pairs`.
- `npairs_k >= 30` → estado normal.

Parámetros configurables globales:

- `min_pairs_exclude = 10`
- `min_pairs_warning = 30`

### 8.3 Impacto en fitting

- Lags excluidos no entran al objetivo de optimización.
- Lags en warning sí entran, con peso reducido opcional `weight_factor_low_pairs`.

### 8.4 Comportamiento visual obligatorio

- `excluded_from_fit=true`: punto experimental con opacidad ≤ 35%, marcador hueco, etiqueta `EXCLUDED`.
- `low_pairs`: punto en color `state.warning`, tooltip con `npairs` y texto `low_pairs`.
- `ok`: estilo normal de serie experimental.
- barra `npairs` de lags excluidos debe renderizarse en patrón rayado para evitar interpretación errónea.

### 8.5 Pesos por lag

Por defecto:

\[
w_k = npairs_k
\]

Alternativo robusto:

\[
w_k = \frac{npairs_k}{\hat{\gamma}(h_k)^2 + \varepsilon}
\]

Normalización opcional:

\[
\tilde{w}_k = \frac{w_k}{\sum w_k}
\]

---

## 9) Gráficos obligatorios

1. **Mapa variográfico** (polar/XY; opcional 3D).
2. **Variograma principal** (puntos exp + curva + barras npairs).
3. **Comparativo direccional** (omni/mayor/menor/vertical).
4. **Pares por lag** (always-on o acoplado al principal).
5. **Residuales** (`gamma_exp - gamma_model`).
6. **Matriz multivariable NxN** (directos/cross).
7. **PSD/eigenvalues por estructura**.

---

## 10) Especificación matemática mínima

### 10.1 Semivariograma experimental directo

\[
\hat{\gamma}(h_k)=\frac{1}{2|N(h_k)|}\sum_{(i,j)\in N(h_k)}[z(x_i)-z(x_j)]^2
\]

### 10.2 Variograma cruzado experimental

\[
\hat{\gamma}_{ij}(h_k)=\frac{1}{2|N(h_k)|}\sum_{(\alpha,\beta)\in N(h_k)}[z_i(x_\alpha)-z_i(x_\beta)][z_j(x_\alpha)-z_j(x_\beta)]
\]

Propiedades:

- puede ser negativo;
- simétrico por índices;
- no admite desfase temporal;
- no calculable en heterotopía total.

## Model Parameter Conventions

### 10.3 Modelos soportados y convención de rango

**Convención oficial y única:** UI, backend y JSON deben exponer `range_display = practical_range_95` para **todos** los modelos con rango finito.  
El parámetro interno del motor (`range_param`) puede variar por modelo, pero la capa de aplicación siempre serializa y muestra `practical_range_95`.

| Modelo | Forma | Parámetro interno | Conversión a `practical_range_95` |
|---|---|---|---|
| Nugget | discontinuidad en origen | `c0` | n/a |
| Spherical | con meseta | `a` | `a` |
| Exponential | asintótico | `a` | `~3a` |
| Gaussian | asintótico | `a` | `~sqrt(3)a` |
| Cubic | con meseta | `a` | `a` |
| Power | sin meseta | `omega, p` | no aplica |

Reglas:

- `power` permitido solo en modo exploratorio (`exploratory_only=true`).
- publicación bloqueada si existe `power` y `allow_power_publish=false`.
- para modelos con rango finito (`spherical`, `exponential`, `gaussian`, `cubic`), `practical_range_95` es el valor normativo para validaciones, UX y exportación.

### 10.4 LMR (univariado)

\[
\gamma(h)=\sum_{s=1}^{S} c_s g_s(h), \quad c_s\ge0
\]

## LMC Constraints (Multivariable)

### 10.5 LMC Constraints (multivariable)

\[
\Gamma(h)=\sum_{s=1}^{S} C_s g_s(h)
\]

Reglas duras:

1. Todas las variables comparten exactamente las mismas estructuras `g_s(h)`.
2. Solo cambian matrices de mesetas `C_s`.
3. Cada `C_s` debe ser simétrica PSD.

Validación:

- Si `n_variables=2`: `|c12^{(s)}| <= sqrt(c11^{(s)} c22^{(s)})`.
- Equivalente obligatorio en backend (`n=2`): `det(C_s)=c11*c22-c12^2 >= -eps_psd`.
- Si `n_variables>2`: `lambda_min(C_s) >= -eps_psd`.
- Default `eps_psd = 1e-10`.

UI:

- estructura inválida resaltada en rojo;
- tooltip con autovalor mínimo y estructura conflictiva;
- publicación bloqueada.

---

## 11) Auto-Fit Rules

### 11.1 Función objetivo

\[
SSE(\theta)=\sum_{k \in K_{fit}} w_k\left(\hat{\gamma}(h_k)-\gamma(h_k;\theta)\right)^2
\]

`K_fit` excluye lags con `excluded_from_fit=true`.

### 11.2 Parámetros optimizables

- `nugget`
- `sills parciales`
- `ranges` (o equivalentes internos)
- opcional: orientación si `fit_orientation=true`.

### 11.3 Restricciones

- `sill >= 0`
- `range > 0`
- `major >= minor >= vertical`
- LMC PSD válido en cada iteración (multivariable).

### 11.4 Optimización

- algoritmo por defecto: `bounded_least_squares`.
- `max_iterations = 500`
- `tolerance = 1e-6`
- parada adicional si mejora relativa `< 1e-8` por 20 iteraciones.

### 11.5 Modos

- `fit_sills_only`
- `fit_ranges_only`
- `full_fit`

### 11.6 Resultado de auto-fit

Debe devolver:

- parámetros ajustados;
- métricas (`sse_weighted`, `rmse_gamma`, `score_global`);
- flags de convergencia;
- warnings de restricciones activas.

---

## 12) Trend and Stationarity Handling

La variografía experimental asume estacionaridad intrínseca.

Opciones de entrada:

- `raw_values`
- `detrended_residuals`

Reglas:

- si `trend_test_enabled=true`, ejecutar chequeo de tendencia (p.ej. regresión vs coordenadas o drift surfaces).
- si se detecta tendencia fuerte (`trend_pvalue < alpha` o `r2_trend > threshold`), mostrar warning `possible_non_stationarity`.
- publicación permite continuar solo si el usuario confirma (`override_non_stationarity=true`) y queda auditado.

---

## 13) Support and Compositing Rules

- Variografía opera sobre `support_type` explícito: `raw_samples | composites`.
- Si cambia soporte, longitud de compuesto, o campaña principal:
  - invalidar experimental/modelo;
  - bloquear publicación hasta recálculo completo.

Campo obligatorio de sesión: `support_signature_hash`.

---

## 14) Tabla de estructuras del modelo

### 14.1 Columnas mínimas

- `id_estructura`, `active`, `model_type`, `nugget_flag`
- `sill_partial` / `sill_matrix`
- `range_major`, `range_minor`, `range_vertical`
- `azimuth`, `dip`, `plunge`
- `practical_range_flag`, `shared_geometry_flag`
- `locked_parameters`, `color`

### 14.2 Reglas

- si `model_type=nugget`: rangos/orientaciones deshabilitados.
- en multivariable: edición de `sill_matrix` dispara PSD inmediato.
- selección de estructura resalta su contribución en curva y elipsoide.

---

## 15) Performance & Caching Rules

### 15.1 Cache de pares

Clave mínima:

`(dataset_id, domain_id, variable_set, support_signature_hash, lag_params, direction_params, estimator)`

### 15.2 Recompute rules

- cambio de variable/filtros/soporte/parámetros de lag o dirección → **recompute experimental**.
- cambio solo de parámetros de modelo (sills/ranges/tipo estructura) → **no recompute pares**, sí recalcular curva/fit.
- cambio de geometría compartida multivariable → recompute curvas modeladas para toda matriz.

### 15.3 Estados de consistencia

- `clean`: experimental + modelo sincronizados con controles.
- `dirty_experimental`: requiere recalcular pares/experimental.
- `dirty_model`: experimental vigente, modelo desactualizado.

Publicación permitida solo en `clean`.

---

## 16) UX behavior rules

- Hover en punto experimental: `lag_center`, `gamma_exp`, `gamma_model`, `npairs`, `residual`, `excluded_from_fit`.
- Click en punto: selecciona lag y destaca barra `npairs` asociada.
- Click en mapa variográfico: actualiza dirección activa y recalcula variograma direccional.
- Estructura activa: resaltado consistente en tabla + curva + elipsoide.
- Datos insuficientes: render degradado + mensaje explícito (`insufficient_pairs`).
- Colores serie deben respetar tokens de sección 3.2.

---

## 17) JSON Contracts (EXPANSION)

### 17.1 `VariographySession`

```json
{
  "session_id": "uuid",
  "dataset_id": "string",
  "domain_id": "string",
  "mode": "univariate|multivariate",
  "variable_primary": "string",
  "variable_secondary": "string|null",
  "support_type": "raw_samples|composites",
  "support_signature_hash": "sha256",
  "z_inverted": false,
  "filters": {
    "subdomain": null,
    "lithology": null,
    "alteration": null,
    "campaign": null
  },
  "calc_params": {
    "lag_distance": 20.0,
    "n_lags": 16,
    "lag_tolerance": 10.0,
    "max_distance": 320.0,
    "min_distance": 0.0,
    "azimuth": 35.0,
    "dip": 10.0,
    "plunge": 0.0,
    "ang_tol_h": 22.5,
    "ang_tol_v": 22.5,
    "band_width": 40.0,
    "band_height": 40.0,
    "vertical_tolerance": null,
    "bin_assignment_mode": "unique_nearest_bin",
    "estimator": "classical"
  },
  "status": "clean|dirty_experimental|dirty_model",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

### 17.2 `ExperimentalVariogram`

```json
{
  "session_id": "uuid",
  "direction_id": "omni|major|minor|vertical|custom",
  "direction_vector": [0.57, 0.82, -0.05],
  "is_omni": false,
  "lag_index": 1,
  "lag_center": 20.0,
  "lag_tolerance": 10.0,
  "gamma_value": 0.145,
  "npairs": 183,
  "is_valid": true,
  "excluded_from_fit": false,
  "quality_flag": "ok|low_pairs|excluded",
  "estimator_type": "classical"
}
```

### 17.3 `VariogramModel`

```json
{
  "model_id": "uuid",
  "session_id": "uuid",
  "is_multivariate": false,
  "version": 3,
  "status": "draft|validated|published",
  "fit_mode": "fit_sills_only|fit_ranges_only|full_fit",
  "fit_metrics": {
    "sse_weighted_pairs": 12.31,
    "rmse_gamma": 0.041,
    "score_global": "acceptable"
  },
  "optimizer": {
    "algorithm": "bounded_least_squares",
    "max_iterations": 500,
    "tolerance": 1e-6,
    "converged": true
  },
  "published_flag": false
}
```

### 17.4 `ModelStructure`

```json
{
  "model_id": "uuid",
  "structure_index": 1,
  "type": "nugget|spherical|exponential|gaussian|cubic|power",
  "active": true,
  "practical_range_flag": true,
  "shared_geometry_flag": false,
  "locked_parameters": {
    "sill": false,
    "range": false,
    "orientation": true
  },
  "anisotropy": {
    "range_major": 180.0,
    "range_minor": 95.0,
    "range_vertical": 60.0,
    "azimuth": 35.0,
    "dip": 10.0,
    "plunge": 0.0
  },
  "sill": {
    "univariate": 0.22,
    "matrix": null
  }
}
```

### 17.5 `ModelValidation`

```json
{
  "model_id": "uuid",
  "psd_ok": true,
  "eigenvalues_by_structure": {
    "1": [0.12, 0.03],
    "2": [0.07, 0.01]
  },
  "hard_blockers": [],
  "warnings": [
    "Pocos pares en los últimos 2 lags"
  ],
  "residual_summary": {
    "mean": 0.002,
    "std": 0.041,
    "p95_abs": 0.09
  }
}
```

---

## 18) Hard Blockers for Publish

Un modelo **no puede** publicarse si existe al menos uno:

1. `psd_ok=false` (multivariable).
2. `hard_blocker=insufficient_pairs_global`.
3. sin estructuras activas válidas (`n_active_structures=0`).
4. estado `dirty_experimental` o `dirty_model`.
5. uso de `power` con `allow_power_publish=false`.
6. heterotopía total en cruzados requeridos para cokriging.

---

## 19) Criterios de aceptación

La implementación se considera completa cuando:

1. No hay ambigüedad en geometría, pares, lags, modelos, anisotropía y LMC.
2. El cálculo de `N(h)` sigue exactamente sección 7.
3. El ajuste usa pesos y exclusión de lags según sección 8 y 11.
4. Los modelos multivariables inválidos (PSD) son imposibles de publicar.
5. Toda invalidación/recompute respeta sección 15.
6. Todos los parámetros relevantes quedan serializados en JSON y permiten reproducir resultados.
7. UI presenta estados de calidad de datos y warnings sin ocultar `npairs`.

---

## 20) No objetivos (guardrails)

- No saturar la UI con mini-gráficos redundantes.
- No ocultar pares por lag.
- No ajustar directos y cruzados de forma independiente en multivariable.
- No permitir “publicar igual” ante bloqueos duros.
- No reemplazar criterio geológico por mínimo error numérico sin contexto.

---

## 21) Recomendaciones operativas

- Mantener workflow estándar: omni → mayor → menor → vertical.
- Revisar primero calidad de lags y anisotropía antes de auto-fit.
- Usar residuales + npairs + PSD como tríada mínima de validación.
- Auditar decisiones de override (trend/no estacionaridad y bloqueos).
