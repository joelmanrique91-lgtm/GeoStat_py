# VISUAL ARCHITECTURE STATUS

Fecha: 2026-03-22  
Estado: checkpoint técnico estable (sin cambios de cálculo/workflow/contratos)

---

## 1) Estado actual

La capa visual del proyecto quedó desacoplada respecto del panel principal y organizada por renderers concretos.
El sistema mantiene el stack operativo actual (**CustomTkinter + Matplotlib/TkAgg**) como backend efectivo de runtime.

No se cambiaron:
- lógica de negocio,
- cálculo geoestadístico,
- contratos de datos visuales,
- workflow de etapas.

---

## 2) Qué se desacopló

Se removió del `HomePanel` el detalle de trazado de:
- EDA,
- espacial 2D,
- espacial 3D.

`HomePanel` ahora actúa como orquestador de render y selección de backend 3D.

---

## 3) Renderers disponibles

Paquete: `app/ui/renderers/`

- `base.py`
  - interfaces `EDARenderer`, `Spatial2DRenderer`, `Spatial3DRenderer`;
  - contextos `EDARenderContext`, `Spatial2DRenderContext`.
- `mpl_eda_renderer.py`
  - implementación Matplotlib para vista EDA.
- `mpl_spatial2d_renderer.py`
  - implementación Matplotlib para XY/XZ/YZ + panel informativo.
- `mpl_spatial3d_renderer.py`
  - adapter Matplotlib 3D sobre `Spatial3DView`.
- `pyvista_spatial3d_renderer.py`
  - candidato alternativo 3D (pilotado, no habilitado en runtime actual).

---

## 4) Qué backend 3D está activo hoy

Backend activo real: **Matplotlib 3D (`mpl_toolkits.mplot3d`)**.

El candidato PyVista está cableado pero deshabilitado por disponibilidad/integración de runtime en esta fase.

---

## 5) Cómo funciona el fallback 3D

Flujo de selección en `HomePanel`:
1. Se evalúa disponibilidad del renderer PyVista.
2. Si no está disponible o no está habilitado, se selecciona renderer Matplotlib 3D.
3. Se registra evento de fallback en activity log con motivo.
4. Si el renderer activo falla al renderizar, la UI vuelve automáticamente a 2D.

Este fallback mantiene continuidad operativa sin tocar contratos ni servicios.

---

## 6) Mejoras visuales ya implementadas

### EDA
- mejor separación visual de histogramas y capas base/activa;
- márgenes y empaquetado más limpios;
- mejora de legibilidad en QQ y boxplots.

### Espacial 2D
- composición más clara XY/XZ/YZ;
- colorbar más compacta;
- panel informativo con mejor espaciado y lectura.

### Espacial 3D (Matplotlib)
- cámara inicial y reset refinados;
- pane colors y grilla más limpios;
- ajuste de aspecto por spans reales X/Y/Z;
- tamaño/alpha de marcador adaptados a densidad de puntos.

### Tema general
- tokens de chart y estilo de ejes ajustados para una lectura más profesional.

---

## 7) Limitaciones vigentes

- El 3D sigue limitado por capacidad intrínseca de Matplotlib (`mplot3d`) en interacción avanzada.
- PyVista aún no está habilitado para uso embebido con Tk en este checkpoint.
- El `HomePanel` continúa siendo un archivo grande (aunque con menor acoplamiento de render).

---

## 8) Próximo paso recomendado

No abrir una nueva migración completa todavía.

Siguiente paso controlado recomendado:
1. validar estrategia de integración embebida/no bloqueante para PyVista en entorno objetivo;
2. habilitar piloto real detrás de `Spatial3DRenderer` sin alterar contratos;
3. agregar pruebas específicas de selección de backend y fallback.

---

## 9) Riesgos / deuda técnica

- Riesgo de integración de event-loop entre Tk y backend 3D alternativo.
- Dependencia de disponibilidad de `pyvista`/`vtk` en entorno de ejecución final.
- Necesidad de tests dirigidos a runtime visual (backend selection / graceful fallback).
