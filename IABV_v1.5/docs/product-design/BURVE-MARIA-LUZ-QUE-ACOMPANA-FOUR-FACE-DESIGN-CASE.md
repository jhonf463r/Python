# BURVE — MARÍA: LUZ QUE ACOMPAÑA
## Expediente vivo de diseño: farol de cuatro caras

**Task ID:** `BURVE_FOUR_FACE_LANTERN_DESIGN_AND_MARKET_FIT_20261031`  
**Fecha:** 2026-10-31  
**Estado:** `ACTIVE_DESIGN_TRACK / CONCEPT_NOT_LOCKED / VECTOR_MASTER_NOT_ESTABLISHED`  
**Alcance actual:** investigación, dirección artística, arquitectura visual de cuatro caras y documentación. No incluye liberar CAM, fabricar, configurar la máquina ni afirmar validación física.

> **Arranque de chat nuevo:** leer el `CURRENT-STATE.md` de la revisión viva de PR #579/esta rama; después este expediente y [LASER_VECTOR_TOPOLOGY](../runbooks/laser-cut-vector-topology-skill.md). Esta rama aún no está integrada en `main`, por lo que un chat que lea únicamente `main` no encontrará todavía esta ruta.

## 1. Objetivo del propietario

Diseñar las cuatro caras laterales del farol BURVE de modo que el objeto sea coherente al girarlo, reconocible como pieza mariana, atractivo como producto decorativo premium y fabricable en MDF con iluminación LED cálida. La pregunta central es cuántos diseños maestros se necesitan y cómo se distribuyen; no basta con producir cuatro imágenes inconexas.

El propietario ha solicitado explícitamente cuatro caras. Los archivos anteriores se concentran sobre todo en un panel frontal; no demuestran por sí mismos la geometría completa del cuerpo, las uniones ni que los cuatro paneles tengan dimensiones idénticas.

## 2. Arquitectura visual recomendada: dos parejas opuestas (2+2)

**Cara A1 y A3, opuestas:** la misma composición principal de María sola, medio cuerpo, cabeza suavemente inclinada, manos en oración, halo circular integrado y manto de curvas amplias.

**Cara B1 y B3, opuestas:** la misma composición complementaria: un lirio mariano estilizado, con arco de luz discreto y la leyenda grabada `LUZ QUE ACOMPAÑA` solo si resulta legible a tamaño real. Si el texto no cabe con elegancia, usar solo el emblema floral.

Son dos diseños maestros para cuatro paneles. Las parejas comparten proporciones, perfil, márgenes, lenguaje de curvas, tratamiento de luz, acabado y uniones.

### Comparación de arquitecturas

| Opción | Ventaja | Riesgo | Evaluación inicial |
|---|---|---|---|
| Cuatro caras iguales con María | Máxima repetición del motivo principal; baja variedad | Repetición visual y menor relato al girar | Alternativa de control |
| **Dos parejas 2+2** | Identidad + variedad controlada; dos maestros; ritmo en el volumen | Depende de un emblema secundario bien resuelto | **Recomendada para primera propuesta** |
| Cuatro caras distintas | Variedad narrativa | Fragmenta la identidad, aumenta complejidad y esfuerzo vectorial | No recomendada como primera versión |

No añadir escenas distintas (cruz, paloma, corazón, rosas, etc.) solo para llenar paneles. No introducir al Niño Jesús en el maestro A sin una decisión nueva del propietario: la referencia visual más reciente presenta a María sola.

## 3. Diseño de los dos maestros

### Maestro A — María
- María sola, medio cuerpo, expresión serena y maternal, manos juntas en oración.
- Halo circular dentro de la ilustración. No confundirlo con el perfil trapezoidal ni añadir un aro independiente.
- Rostro opaco y continuo: ojos, cejas, nariz, filtrum y labios como grabado superficial, no como huecos pasantes.
- Manto con pocas aberturas grandes y curvas orgánicas. Principio central: **menos cortes, más intención, más luz**.
- El rostro debe seguir reconociéndose en miniatura y con el farol apagado.

### Maestro B — emblema mariano
- Lirio de tres pétalos estilizados, con tallo/hojas integrados y una curva de luz que dialogue con el halo del maestro A.
- Nervaduras/detalles pequeños como grabado superficial, no como piezas cortadas pequeñas.
- Pocas aberturas grandes si aportan luz real; evitar filigrana densa y puentes finos.
- Texto opcional grabado: `LUZ QUE ACOMPAÑA`; omitirlo si la escala impide buena lectura.
- El lirio blanco se asocia tradicionalmente con la pureza de María en la iconografía cristiana; usarlo con sobriedad, no como ornamento genérico.

## 4. Evidencia recuperada y discrepancias de archivos

### Fuente geométrica original
El SVG original del propietario se guarda como [1FarolPVirgen3-owner-source.svg](assets/1FarolPVirgen3-owner-source.svg). Declara lienzo `14 cm × 14 cm` y `viewBox="0 0 140 140"`; eso describe el lienzo, no confirma la medida física final del panel. La geometría roja corresponde al perfil/trayectorias originales del panel trapezoidal y sus rasgos de borde/ensamble. **No es el halo de María.** Hay que confirmar la operación CAM exacta de cada trazo rojo antes de liberar corte.

### Paquete visual más reciente
El paquete `BURVE_MARIA_DISENO_COMPLETO_REVISION.zip` (2026-10-31) contiene vistas PNG y una auditoría JSON/texto; no entrega un SVG maestro editable que combine el perfil exacto con la ilustración. Sus vistas preservadas:
- [Frente trapezoidal de María sola](assets/BURVE-MARIA-four-panel-front-concept.png)
- [Máscara corregida conceptual](assets/BURVE-MARIA-corrected-mask-concept.png)
- [Detalle del rostro](assets/BURVE-MARIA-face-detail-concept.png)
- [Render artístico LED cálido](assets/BURVE-MARIA-warm-LED-render-concept.png)

El PNG es concepto visual, no archivo CAM.

### Conflicto entre versiones previas
El preview recuperado de `BURVE_Maria_Fabricacion.svg` muestra a María con el Niño, mientras que el último frente conceptual muestra a María sola. Esas salidas no representan una misma composición. No mezclar ese SVG/DXF antiguo ni sus capas `Grabado_*.svg` con el último PNG como si fueran un solo maestro definitivo.

El informe técnico anterior declara medidas de 180 × 240 mm, MDF nominal 6 mm, halo de 115,8 mm y longitudes de trayectoria. No se ha demostrado que esas métricas correspondan al lienzo original de 14 × 14 cm ni al último frente trapezoidal. No reutilizarlas como cotas maestras de las cuatro caras hasta reconciliar los archivos.

### Alerta de conectividad del paquete visual
La auditoría del paquete más reciente registra una máscara raster a 1400 × 1400 con 1 componente mayor de 10 píxeles, pero la erosión da: 0,2 mm → 1 componente; 0,5 mm → 2; 1,0 mm → 74; 1,5 mm → 58; 2,0 mm → 62. Esto evidencia sensibilidad a puentes estrechos. Los conteos raster no certifican anchura mecánica ni resistencia. Se requiere reconstrucción vectorial, medición de anchos mínimos y modelo de corte con kerf real.

## 5. Convenciones y reglas no negociables

| Código visual | Significado |
|---|---|
| Negro | MDF que permanece |
| Blanco | hueco / material retirado mediante corte pasante |
| Azul | grabado superficial; no cortar |
| Rojo original | geometría/trayectoria del panel; operación CAM pendiente de mapear |

El rostro debe permanecer negro/opaco y conectado. El halo es un motivo dentro del panel. Una unión visual no demuestra continuidad física. No transferir al BURVE las especificaciones de triplex de 3 mm de otros productos: el brief de este farol declara MDF nominal de 6 mm, pero el espesor real se debe confirmar con calibre.

## 6. Investigación perceptual, comercial e iconográfica (verificada 2026-10-31)

La evidencia permite formular hipótesis de diseño; no permite garantizar ventas ni atribuir efectos cerebrales específicos a un símbolo.

1. **Armonía de producto.** Peng, Eisend y Chen, *A Meta-Analysis of Product Visual Aesthetics*, online 25-06-2025, *Journal of Marketing*. Sintetiza 727 tamaños de efecto de 263 muestras independientes (1993–2024): las propiedades estéticas organizacionales y significativas favorecen la estética percibida y la armonía es la propiedad más fuerte; la estética visual influye en actitudes y comportamientos, con moderadores y una brecha actitud–conducta. Aplicación: las cuatro caras deben sentirse un solo producto. No prueba que 2+2 venda más que cuatro caras idénticas. https://doi.org/10.1177/00222429251356484

2. **Complejidad de imágenes online.** Leng et al., *Designing Online Product Displays: How Visual Complexity Shapes Consumer Product Attitude*, *International Journal of Consumer Studies*, publicado 05-07-2026. Una observación de marketplace y tres experimentos de escenarios encontraron que más complejidad en imágenes de productos hedónicos mejora actitudes, mientras que perjudica actitudes hacia utilitarios; la complejidad debe entenderse en contexto. BURVE es decorativo/hedónico, pero el estudio trata imágenes de exhibición ecommerce, no demuestra que más perforaciones o detalles físicos aumenten ventas. Aplicación: mostrar variedad de ángulos en el anuncio, manteniendo orden en el objeto. https://doi.org/10.1111/ijcs.70229

3. **Simetría y packaging.** *Symmetry influences packaging aesthetic evaluation and purchase intention*, *International Journal of Retail & Distribution Management* (2018), experimento intra-sujetos con 104 participantes. La simetría vertical redujo complejidad percibida y favoreció la fluidez perceptual; la evaluación estética del envase se relacionó con intención de compra. Es evidencia de packaging, no de faroles. Aplicación moderada: las caras opuestas repiten su composición exacta. https://doi.org/10.1108/IJRDM-06-2017-0123

4. **Estructura perceptual y comunicación.** Li, Lee y Blasco-Arcas, meta-análisis de comunicación visual de marketing (883 efectos, 176 estudios; EMAC 2025): el resumen indica que el contenido emocional favorece engagement, el informativo contribuye a resultados de negocio y la estructura perceptual puede ser más eficaz que la complejidad. Aplicación: imagen principal emocional de María y vistas auxiliares claras que expliquen caras, luz, material y dimensiones. No es prueba de ventas de BURVE. https://proceedings.emac-online.org/pdfs/A2021-94666.pdf

5. **Lirio mariano.** National Gallery, Londres: el lirio blanco se relaciona tradicionalmente con pureza y con la Virgen María. Salvador González (Universidad Complutense de Madrid, 2014) estudia los motivos florales en iconografía mariana medieval y advierte que los símbolos deben interpretarse en su contexto. https://www.nationalgallery.org.uk/paintings/glossary/lilies — https://doi.org/10.5209/eiko.73394

6. **Escaneo de referencias de mercado.** Se encontraron faroles de madera con el mismo motivo repetido en caras (Daisy Cube Light) y otros con patrones coordinados por panel. Son precedentes visuales, no datos comparativos de ventas. En Colombia aparecen fabricantes de decoración MDF/corte láser (Artequendama) y productos religiosos MDF (CeGrafic), pero no se localizó evidencia pública suficiente de ventas de un farol mariano comparable de cuatro lados. https://marisherrcollections.com.au/products/fern-cube-light-copy — https://artequendama.com.co/ — https://cegrafic.com/product/virgen-de-guadalupe/

### Implicaciones de venta
- Primera imagen del catálogo: vista 3/4 con una cara A (María) y una B (lirio), mostrando que el diseño continúa alrededor del volumen.
- Carrusel: frontal apagado; 3/4 encendido; detalle del rostro; cara B; vista completa de cuatro lados; dimensiones/materiales.
- Mantener el mismo objeto y geometría en todas las fotos; el render LED no prueba fotometría.
- La percepción premium también depende de cantos, acabado, alineación, uniones, difusor, estabilidad y uniformidad de luz.
- No afirmar “compra inconsciente”, activación cerebral ni aumentos de ventas sin experimento específico.

## 7. Prueba comercial pendiente

Comparar tres mockups con el mismo tamaño, material, iluminación y precio de referencia:
A) cuatro Marías iguales; B) dos parejas 2+2; C) cuatro caras distintas pero coordinadas. Alternar el orden de exposición; medir reconocimiento, preferencia, percepción de calidad/regalo, comprensión del diseño completo e intención de compra. Una exploración inicial con 15–30 personas del público objetivo orienta el diseño, pero no representa el mercado nacional. Si se publica en ecommerce, observar CTR, consultas, carrito y compra real; no confundir intención declarada con venta.

## 8. Estado técnico

- Cuatro caras: objetivo confirmado; medidas/uniones del volumen completo pendientes.
- Perfil original trapezoidal: fuente recuperada; conservar la geometría roja.
- Frente María sola: PNG conceptual disponible.
- Maestro SVG/DXF editable que reproduzca exactamente el PNG y el perfil original: **NO ESTABLECIDO**.
- SVG/DXF antiguo: composición discrepante María + Niño; no es maestro del PNG actual.
- Máscara: raster provisional con alerta de erosión; anchos mecánicos sin validar.
- Kerf, puentes, ensamble, LED/difusor y temperatura: no probados.
- Corte físico / CAM / producción: **NO LIBERADOS**.

## 9. Próxima secuencia y handoff

1. Reconciliar el perfil y las uniones del cuerpo: comprobar si las cuatro caras comparten la misma plantilla trapezoidal.
2. Crear una hoja conceptual de las cuatro caras: A1/A3 María; B1/B3 lirio; vistas ortogonales y 3/4; apagada y encendida.
3. Comparar visualmente con la alternativa de cuatro caras María antes de fijar el diseño.
4. Revisión del propietario: belleza, reconocimiento, calidad facial, coherencia religiosa, lectura a escala y percepción premium.
5. Construir un único maestro vectorial editable para A y otro para B; producir renders/máscaras desde esos maestros.
6. Aplicar [LASER_VECTOR_TOPOLOGY](../runbooks/laser-cut-vector-topology-skill.md) a corte/engrave/topología/kerf.
7. Solo tras autorización específica, preparar CAM/probetas y validar fabricación e iluminación.

**IA DESTINO para el siguiente paso:** ChatGPT — dirección artística y lámina conceptual 2+2, sin afirmar liberación CAM.  
**Verificador posterior:** Codex para reconciliación SVG/geometría vectorial cuando el propietario elija composición y estén confirmadas dimensiones/uniones.  
**Stop condition:** si el perfil común/ensamble no están definidos, entregar concepto visual marcado como tal, nunca archivo de fabricación.
