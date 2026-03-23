# Especificación funcional y visual — Pestaña **06 Variografía** (GeoStat Py)

## 1) Objetivo

Definir una pestaña de variografía con enfoque técnico de geoestadística aplicada, orientada a:

- diagnóstico de continuidad espacial;
- identificación y modelamiento de anisotropía;
- ajuste de modelos variográficos univariados y multivariables;
- validación matemática para kriging/cokriging;
- trazabilidad reproducible del proceso de modelamiento.

La pestaña debe operar como tablero reactivo (estilo analítico tipo Power BI), pero con jerarquía visual y controles propios del flujo geoestadístico.

---

## 2) Alcance funcional

### 2.1 Modos de trabajo

1. **Modo A — Exploración univariable**
   - mapa variográfico;
   - variogramas experimentales omni/direccionales;
   - detección de anisotropías;
   - ajuste de modelo directo.

2. **Modo B — Validación geométrica**
   - estabilidad por lag, tolerancias y número de pares;
   - comparación por dominios/subdominios/litologías.

3. **Modo C — Modelamiento multivariable**
   - variogramas directos y cruzados;
   - ajuste por estructura con LMC;
   - validación PSD de matrices de mesetas por estructura.

4. **Modo D — Preparación para estimación**
   - publicación del modelo a kriging/cokriging;
   - versionado de parámetros;
   - auditoría técnica de decisiones.

---

## 3) Diseño visual y UX

### 3.1 Dirección de arte

- Estética oscura técnica (minería/geoestadística), no corporativa genérica.
- Alta legibilidad de curvas, nubes y mapas.
- Mínimo ruido visual y foco en diagnóstico.

### 3.2 Paleta sugerida

- **Fondo:** azul petróleo / grafito oscuro.
- **Paneles:** gris-azulado oscuro, contraste moderado.
- **Acento activo:** azul eléctrico tenue.
- **Series:**
  - experimental: gris claro;
  - modelo: ámbar o cian suave;
  - dirección mayor: verde azulado;
  - dirección menor: violeta suave;
  - vertical: naranja tenue.
- **Estados:**
  - warning: amarillo;
  - error/PSD inválido: rojo suave.

---

## 4) Layout de la pestaña

## 4.1 Franjas funcionales

1. **Franja 1 — Encabezado contextual**
   - dataset activo;
   - variable principal/secundaria;
   - dominio/filtro;
   - compuesto/soporte;
   - modo (uni/multivariable);
   - estado del modelo (sin calcular, experimental, preliminar, validado, publicado).

2. **Franja 2 — Barra de filtros y parámetros**
   - controles compactos tipo slicer;
   - acciones primarias: `Calcular`, `Autoajuste`, `Reset modelo`, `Guardar versión`.

3. **Franja 3 — KPI cards geoestadísticas**
   - N válidos, N pares, lag, # lags, distancia máxima;
   - pepita %, sill total, rangos mayor/menor/vertical, relación anisotrópica;
   - score de ajuste;
   - estado matemático (válido / insuficiente / PSD inválido / pocos pares).

4. **Franja 4 — Zona analítica principal**
   - **Panel A:** mapa variográfico / rosa direccional (dominante);
   - **Panel B:** variograma experimental + modelo + barras de pares;
   - **Panel C:** tabla editable de estructuras;
   - **Panel D:** diagnóstico (residuales, pares por lag, PSD/eigenvalues, log técnico).

5. **Franja 5 — Pie técnico colapsable**
   - bitácora reproducible: timestamp, filtros, versión de datos, parámetros, warnings.

### 4.2 Distribución recomendada

- Columna izquierda (25%): controles.
- Columna central (50%): mapa variográfico (arriba) + variograma principal (abajo).
- Columna derecha (25%): KPIs + tabla estructuras + diagnóstico.
- Franja inferior: log/versiones.

---

## 5) Componentes y contratos UI

## 5.1 Selectores principales

- `dropdown_variable_principal`
- `toggle_multivariable`
- `dropdown_variable_secundaria` (visible solo en multivariable)

**Reglas**

- Prohibir secundaria = principal.
- Si existe heterotopía total, deshabilitar variograma cruzado experimental y mostrar warning.

## 5.2 Selector geológico/filtros

- `dominio`, `subdominio`, `litologia`, `alteracion`, `fase_mineral`, `campania`.

**Regla:** cambios invalidan cache de pares y fuerzan recálculo.

## 5.3 Parámetros de cálculo

- `lag_distance`, `n_lags`, `lag_tolerance`, `max_distance`, `auto_lag`.
- Direccionalidad: `azimuth`, `dip`, `plunge`, tolerancias angulares, `band_width`, `band_height`.

**Sugerencias automáticas iniciales**

- `max_distance ≈ 0.5 * diagonal_dominio`.
- `n_lags = 12..20`.
- `lag_distance = max_distance / n_lags`.

**Warnings**

- `lag_tolerance > 0.5 * lag_distance`.
- pocos pares en lags finales.

## 5.4 Tipos de variograma

- semivariograma clásico (default), covarianza, correlograma, madograma, indicador, relativo.

## 5.5 Opciones robustas

- estimador clásico / Cressie-Hawkins;
- remover outliers por pares extremos;
- estandarizar por varianza;
- ponderar por número de pares.

## 5.6 Acciones de modelamiento

- `agregar_estructura`, `eliminar_estructura`, `clonar_estructura`;
- `autoajuste`, `bloquear_anisotropia_comun`, `bloquear_sills`;
- `fit_solo_sills`, `fit_solo_ranges`, `copiar_geometria`.

## 5.7 Publicación

- `guardar_borrador`, `marcar_validado`, `publicar_kriging`, `publicar_cokriging`, `export_json`, `export_yaml`, `export_pdf`.

---

## 6) Gráficos obligatorios

1. **Mapa variográfico** (2D/polar, opcional 3D).
2. **Variograma principal** (puntos exp + curva modelo + barras pares + tooltips).
3. **Comparativo direccional** (omni, mayor, menor, vertical).
4. **Pares por lag** (siempre visible/activable).
5. **Residuales** (`gamma_exp - gamma_model`).
6. **Matriz multivariable NxN** (directos en diagonal, cruzados fuera).
7. **Panel PSD/autovalores por estructura**.

---

## 7) Especificación matemática mínima

## 7.1 Semivariograma experimental directo

\[
\hat{\gamma}(h) = \frac{1}{2|N(h)|} \sum_{(\alpha,\beta) \in N(h)} [z(x_\alpha)-z(x_\beta)]^2
\]

## 7.2 Variograma cruzado experimental

\[
\hat{\gamma}_{ij}(h) = \frac{1}{2|N(h)|} \sum_{(\alpha,\beta) \in N(h)} [z_i(x_\alpha)-z_i(x_\beta)] [z_j(x_\alpha)-z_j(x_\beta)]
\]

Propiedades UI relevantes:

- puede ser negativo;
- simetría por índices;
- no modela retardos;
- no se calcula con heterotopía total.

## 7.3 Modelo lineal de regionalización (univariado)

\[
\gamma(h) = \sum_{s=1}^{S} c_s g_s(h), \quad c_s \ge 0
\]

## 7.4 Modelo lineal de corregionalización (multivariable)

\[
\Gamma(h) = \sum_{s=1}^{S} C_s g_s(h)
\]

Condición de validez: cada matriz \(C_s\) debe ser simétrica semidefinida positiva.

## 7.5 Validación PSD

- 2 variables: verificar \(|c_{12}^{(s)}| \le \sqrt{c_{11}^{(s)} c_{22}^{(s)}}\) por estructura.
- >2 variables: autovalores \(\lambda_k(C_s) \ge -\varepsilon\).

## 7.6 Ajuste recomendado

- `SSE_weighted_pairs`
- `RMSE_gamma`
- `score_global` cualitativo: Excelente / Aceptable / Débil.

Con pesos típicos:

\[
w_k = |N(h_k)| \quad \text{o} \quad w_k = \frac{|N(h_k)|}{\hat{\gamma}(h_k)^2 + \varepsilon}
\]

---

## 8) Tabla de estructuras del modelo

### 8.1 Columnas mínimas

- `id_estructura`, `activa`, `tipo_modelo`, `nugget_flag`, `sill_parcial`
- `range_major`, `range_minor`, `range_vertical`
- `azimuth`, `dip`, `plunge`
- `locked_geometry`, `locked_sill`, `color`

### 8.2 Reglas

- Si `tipo_modelo = pepita`, deshabilitar rangos/orientación.
- En multivariable, cada estructura tiene matriz de sills y validación PSD inmediata.
- Selección de estructura debe resaltar su contribución en curva y elipsoide asociado.

---

## 9) Motor de eventos reactivo

1. Cambio variable → recalcula stats, mapa, experimental, KPIs.
2. Cambio dominio → invalida cache de pares/modelos por dominio.
3. Cambio lag/tolerancias → recalcula pares + experimental + barras confiabilidad.
4. Click mapa variográfico → actualiza azimut/dip y dirección activa.
5. Edición estructura → actualiza curva, residuales, anisotropía, PSD (si aplica).
6. Publicar modelo → validación final, persistencia y snapshot reproducible.

---

## 10) Contratos JSON sugeridos

## 10.1 `VariographySession`

```json
{
  "session_id": "uuid",
  "dataset_id": "string",
  "domain_id": "string",
  "mode": "univariate|multivariate",
  "variable_primary": "string",
  "variable_secondary": "string|null",
  "filters": {
    "subdomain": null,
    "lithology": null,
    "alteration": null,
    "campaign": null
  },
  "calc_params": {
    "lag_distance": 20.0,
    "n_lags": 16,
    "lag_tolerance": 8.0,
    "max_distance": 320.0,
    "azimuth": 35.0,
    "dip": 0.0,
    "plunge": 0.0,
    "ang_tol_h": 22.5,
    "ang_tol_v": 22.5,
    "band_width": 40.0,
    "band_height": 40.0,
    "estimator": "classical"
  },
  "status": "experimental|preliminary|validated|published",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

## 10.2 `ExperimentalVariogram`

```json
{
  "session_id": "uuid",
  "direction_id": "omni|major|minor|vertical|custom",
  "lag_index": 1,
  "lag_center": 20.0,
  "gamma_value": 0.145,
  "npairs": 183,
  "tolerance_meta": {
    "lag_tolerance": 8.0,
    "ang_tol_h": 22.5,
    "ang_tol_v": 22.5
  },
  "estimator_type": "classical"
}
```

## 10.3 `VariogramModel`

```json
{
  "model_id": "uuid",
  "session_id": "uuid",
  "is_multivariate": false,
  "version": 3,
  "status": "draft|validated|published",
  "fit_metrics": {
    "sse_weighted_pairs": 12.31,
    "rmse_gamma": 0.041,
    "score_global": "aceptable"
  },
  "published_flag": false
}
```

## 10.4 `ModelStructure`

```json
{
  "model_id": "uuid",
  "structure_index": 1,
  "type": "nugget|spherical|exponential|gaussian|cubic|power",
  "active": true,
  "anisotropy": {
    "range_major": 180.0,
    "range_minor": 95.0,
    "range_vertical": 60.0,
    "azimuth": 35.0,
    "dip": 0.0,
    "plunge": 0.0
  },
  "sill": {
    "univariate": 0.22,
    "matrix": null
  }
}
```

## 10.5 `ModelValidation`

```json
{
  "model_id": "uuid",
  "psd_ok": true,
  "eigenvalues_by_structure": {
    "1": [0.12, 0.03],
    "2": [0.07, 0.01]
  },
  "warnings": [
    "Pocos pares en los últimos 2 lags"
  ]
}
```

---

## 11) Criterios de aceptación

La implementación se acepta cuando:

1. Cambiar variable/dominio recalcula experimental + KPIs correctamente.
2. El mapa variográfico actualiza direcciones sugeridas/activas.
3. Editar estructuras actualiza curva modelada en vivo.
4. Barras de pares responden a lag/tolerancias.
5. En multivariable, se bloquea publicación de modelos PSD inválidos.
6. Se pueden guardar y reabrir versiones.
7. El modelo publicado queda disponible para kriging/cokriging.
8. El estado completo de la sesión es serializable/reproducible por JSON.

---

## 12) No objetivos (guardrails)

- No saturar UI con exceso de mini-gráficos simultáneos.
- No ocultar número de pares.
- No ajustar directos/cruzados de forma independiente en multivariable.
- No permitir publicación de LMC inválido.
- No reemplazar criterio geológico por ajuste numérico ciego.

---

## 13) Recomendaciones operativas

- Mantener comparación omni/mayor/menor/vertical como flujo estándar.
- Incluir warnings explícitos para deriva, pocos pares y estabilización de sill.
- Conservar trazabilidad completa (auditoría interna + reproducibilidad).

