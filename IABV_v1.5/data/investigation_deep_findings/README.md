# ZONA DE ENTRADA DE HALLAZGOS - INVESTIGACIÓN PROFUNDA

**Fecha de creación:** 2026-06-17  
**Objetivo:** Landing zone para recibir hallazgos de investigación profunda sin rehacer arquitectura.

---

## Estructura de esta carpeta

Esta carpeta está diseñada para recibir y organizar hallazgos de investigación profunda sobre el sistema multimodal de IABV v1.5.

```
data/investigation_deep_findings/
├── README.md                          # Este archivo
├── template_hallazgo.md               # Template para registrar hallazgos
├── hallazgos/                         # Carpeta para hallazgos individuales
│   ├── 001_resumen_ejecutivo.md      # Resumen ejecutivo de la investigación
│   ├── 002_hallazgo_critico_X.md     # Hallazgos críticos individuales
│   └── ...
├── matriz_mapeo_hallazgos_modulos.md # Matriz de mapeo hallazgo → módulo
└── pruebas_reconciliacion/           # Pruebas de reconciliación
    └── ...
```

---

## Cómo usar esta zona

### 1. Registrar un hallazgo

Copiar el template `template_hallazgo.md` a `hallazgos/XXX_descripcion.md` y llenar los campos requeridos.

### 2. Mapear a módulos

Usar `matriz_mapeo_hallazgos_modulos.md` para mapear cada hallazgo a los módulos afectados.

### 3. Definir pruebas

Usar la carpeta `pruebas_reconciliacion/` para definir pruebas específicas para cada hallazgo.

---

## Campos requeridos para cada hallazgo

Cada hallazgo debe incluir:

- **ID:** Identificador único (ej: 001, 002, etc.)
- **Título:** Título descriptivo del hallazgo
- **Resumen ejecutivo:** Resumen breve del hallazgo
- **Hallazgo crítico:** Descripción detallada del problema
- **Riesgos:** Riesgos asociados al hallazgo
- **Sesgos potenciales:** Sesgos que el hallazgo puede introducir
- **Métricas recomendadas:** Métricas para monitorear el hallazgo
- **Módulos afectados:** Lista de módulos afectados
- **Cambios mínimos sugeridos:** Cambios mínimos para corregir el hallazgo
- **Pruebas a ejecutar:** Pruebas para verificar la corrección
- **Severidad:** Severidad del hallazgo (critical, high, medium, low)
- **Estado:** Estado del hallazgo (pending, in_progress, resolved, deferred)

---

## Flujo de trabajo

1. **Investigación profunda** genera hallazgos
2. **Registrar hallazgos** usando el template
3. **Mapear a módulos** usando la matriz
4. **Definir pruebas** en pruebas_reconciliacion/
5. **Aplicar cambios mínimos** si se aprueba
6. **Ejecutar pruebas** para verificar corrección
7. **Actualizar estado** del hallazgo

---

## Criterios para cambios mínimos

Un cambio se considera mínimo si:

- No requiere refactor arquitectónico
- No crea nuevas capas innecesarias
- No altera la base estable (TruthArbitrator, SignalFusionCore, EvidenceRecorder)
- Preserva las correcciones de sesgo aplicadas
- Es reversible si falla
- Tiene pruebas de verificación

---

## Qué NO hacer en esta zona

- No reescribir la arquitectura
- No abrir nuevos frentes sin aprobación
- No inventar servicios nuevos
- No ocultar gaps detrás de simulación
- No confundir evidencia temporal con evidencia persistente

---

**Fin de README - Zona de entrada de hallazgos**
