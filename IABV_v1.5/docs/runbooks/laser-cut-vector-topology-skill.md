# Laser-cut vector topology and manufacturability — reusable capability

**Capability ID:** LASER_VECTOR_TOPOLOGY  
**Version:** 1.0.0  
**Date:** 2026-10-31  
**Type:** Cross-AI skill / manufacturing reasoning runbook  
**Status:** DOCUMENTED_METHOD; AUTOMATED_ENFORCEMENT_AND_PHYSICAL_VALIDATION_NOT_PROVEN  
**Applies to:** SVG, DXF, AI, EPS, PDF-vector and other 2D vector designs intended for laser cutting, engraving or marking.  
**Primary outcome:** Predict, with explicit evidence and uncertainty, which material remains connected to the manufactured part, which material is separated and falls out, which areas are only engraved, and whether the final geometry is suitable for a physical prototype.

---

## 1. Why this capability exists

A laser-cut illustration is not the same thing as a manufacturable laser-cut part.

A visual preview can look correct while the actual cut leaves detached islands, thin fragile webs, unsupported facial features, uncut slugs, gaps at assembly edges or a different outline from the intended product. The central reasoning task is therefore not “does the picture look good?” It is:

**After the machine follows the exact cut trajectories, with the actual kerf and material behavior, what physical regions remain, which of those regions are connected, and which regions are intended to be kept?**

This runbook turns that question into a repeatable process for future ChatGPT, Codex, IABV and other participating agents that retrieve this repository memory.

It is a reusable method, not an assertion that IABV currently has an autonomous laser-design runtime, a CAD kernel, a CAM integration or a tested automatic validator. Those capabilities require separate implementation and evidence.

### Activation triggers

Retrieve and apply this skill whenever a task involves any of the following:

- Designing, repairing, reviewing or optimizing a laser-cut product.
- Interpreting SVG, DXF, AI, EPS or vector PDF paths for cutting or engraving.
- Determining whether black shapes stay, white regions fall out, or individual features become loose pieces.
- Checking a face, hand, letter, halo, ornament, bridge, slot, tab, frame or panel for physical continuity.
- Producing a binary cut mask, engraving layer, DXF, SVG, CAM file, laser-ready template or illuminated-panel design.
- Optimizing the number, length or order of laser operations without losing appearance or strength.
- Reviewing a previous laser-cut attempt whose rendered preview disagrees with the physical result.

### Mandatory principle

Do not infer manufacturing semantics from appearance alone. Establish the source geometry, machine/CAM interpretation, stock boundary, operation mapping and material behavior before declaring what remains or falls away.

---

## 2. Evidence classes: keep fact, convention and assumption separate

Every review must label findings using these classes:

- **SOURCE_FACT:** directly present in the supplied vector file, user specification, machine documentation or material datasheet.
- **OWNER_CONFIRMED_SEMANTICS:** the user explicitly explains what a path, color, edge, dimension or operation means.
- **STANDARD_BEHAVIOR:** a rule defined by SVG, DXF or another applicable format specification.
- **CAM_PROFILE_FACT:** a documented setting in the exact CAM software / machine profile.
- **MEASURED_PROCESS_FACT:** a value measured on the actual machine and material batch, such as kerf or minimum reliable bridge.
- **ENGINEERING_INFERENCE:** a conclusion computed from source geometry and stated assumptions.
- **DESIGN_TARGET:** a chosen threshold to validate, not a proven universal minimum.
- **UNKNOWN / NOT_PROVIDED / NOT_RUN:** evidence that is missing or an action that was not executed.

Never promote an inference into a measured fact. A successful parse is not proof of correct operation mapping; a correct digital topology check is not proof of physical strength; a render is not proof of manufacturability.

If there is no separate technical article supplied, state that clearly. Do not claim to have extracted findings from an article that was not actually available. External standards and papers may be added as separately cited research.

---

## 3. First understand what the vector file means

### 3.1 Inspect the complete document before changing anything

For the exact source file and revision, inspect:

1. File identity, path, revision/hash and original dimensions.
2. Units, width, height, viewBox, coordinate origin and scale.
3. Layers, groups, object IDs, object types and object count.
4. Fill, stroke, stroke width, opacity, fill-rule and visibility.
5. Open and closed subpaths, compound paths and self-intersections.
6. Transforms, nested transforms, clipping paths, masks, symbols, clones and referenced objects.
7. Embedded raster images, text objects, font dependencies and external references.
8. Duplicated, overlapping, coincident or nearly coincident paths.
9. Whether the CAM software interprets colors, layers, line widths or object types as distinct operations.
10. The actual machine profile and any kerf compensation already applied by the CAM.

Preserve the source file. Work on a revisioned copy and record all transformations.

### 3.2 SVG fill is not the same as a laser toolpath

SVG is a graphics language. Its visual fill and stroke rules do not automatically define the manufacturing action.

The W3C SVG 2 specification defines fill as painting the interior of a shape and stroke as painting along its outline. It also states that filling an open subpath behaves as though a closing segment were added between its last and first points. This is important: a path that looks visually closed because it is filled may still be an open path in the source geometry. A CAM operation following the path centerline can behave differently from the visual fill.

SVG compound paths can use different fill rules:

- **nonzero:** insideness is determined by signed path crossings.
- **evenodd:** insideness is determined by whether the number of path crossings is odd or even.

The chosen rule affects which regions appear filled or hollow. Do not count every subpath as a separate physical part, hole or cutout.

Reference: W3C, SVG 2, “Painting: Filling, Stroking and Marker Symbols,” especially fill and fill-rule:  
https://www.w3.org/TR/SVG/latest/painting.html

Reference: W3C, SVG Paths:  
https://www.w3.org/TR/svg-paths/

### 3.3 A stroke width is not a kerf measurement

An SVG stroke width normally controls how the line is rendered. It is not automatically the physical groove width, the machine kerf or an instruction to remove a filled band.

For cutting, many CAM workflows follow a vector line as a centerline. For engraving, a vector path can be followed at shallower settings, while raster engraving scans pixels. The exact interpretation depends on the CAM profile and operation settings.

Aalto University’s laser-cutting guide distinguishes vector cutting from raster/vector engraving and explains that kerf depends on both material and laser settings. It also describes color mapping as a workflow convention, not a universal semantic standard.

Reference: Aalto University, Guide for Digital Design, “Creating a Design for Laser Cutting”:  
https://digitaldesign.aalto.fi/digital-design-workflows/digital-production/laser-cutting/creating-a-design-for-laser-cutting/

Reference: Aalto University, “Introduction to Laser Cutting”:  
https://digitaldesign.aalto.fi/digital-design-workflows/digital-production/laser-cutting/introduction-to-laser-cutting/

### 3.4 Never assume universal color semantics

Red does not universally mean cut; black does not universally mean keep; blue does not universally mean engrave. A particular machine, CAM profile, operator or customer may use a different mapping.

Before interpreting color as operation, retrieve the documented mapping for the exact job. If it is unavailable, ask for it or mark it UNKNOWN. Do not silently guess.

For the BURVE case documented below, the Owner specified this particular convention:

- BLACK = MDF material intended to remain.
- WHITE = region removed by a through-cut.
- BLUE = surface engraving, not a through-cut.
- The red paths in the supplied SVG were confirmed by the Owner as the actual panel boundary / cut geometry for that trapezoidal lantern face. They were not an instruction to add a decorative circular hoop.

That is a case-specific confirmed mapping, not a universal rule for other SVGs.

---

## 4. Define the stock and the operation model

### 4.1 Establish the stock region

Start from the exact physical blank and the product’s intended outer boundary.

Define:

- **S:** the stock region, in real physical units.
- **P:** the intended finished panel boundary.
- **C:** the set of through-cut centerlines / contours.
- **E:** the set of surface engraving operations.
- **M:** material that remains after all through-cut operations have been applied.
- **D:** detached material pieces / slugs / scrap generated by the cuts.

Do not confuse the outer boundary of a trapezoidal panel with a decorative feature inside the panel. If the source contains a real panel perimeter, preserve it as the stock/product boundary unless the Owner explicitly changes the product geometry.

### 4.2 Apply the actual cut width

A vector line is ideally zero-width in geometry, but a physical laser removes material with a nonzero kerf.

If the CAM follows an uncompensated centerline, the removed region can be approximated by sweeping a band of effective width k along the centerline. In computational geometry this may be represented as a buffer / Minkowski sum with radius k/2.

Conceptually:

- C_actual = union of all actual cut sweeps.
- M = S minus C_actual.

This approximation must reflect the real CAM workflow:

- If CAM already offsets the path for kerf compensation, do not apply the same compensation again.
- If the process produces different upper and lower kerfs, use the relevant measured geometry for the design decision.
- For small radii, sharp corners, tight curves or heat-affected areas, a simple constant-width buffer may be insufficient; flag this for physical validation.

### 4.3 Treat engraving separately

Engraving is not a through-cut. It should not be subtracted from the full material thickness when determining whether a part is disconnected.

However, engraving can reduce residual thickness and can weaken narrow bridges if it is deep, dense or close to an edge. Record engraving depth/pass and review the local remaining thickness when structurally relevant.

Use distinct operation layers such as:

- CUT_THROUGH
- ENGRAVE_FACE
- ENGRAVE_DECOR
- MARK (when applicable)
- REFERENCE_NOT_OUTPUT

Use the exact machine/CAM layer-to-operation map. A layer name alone does not prove the machine will execute the intended operation.

---

## 5. Determine what remains, what disconnects and what falls out

This is the core topology procedure.

### 5.1 Run the Boolean manufacturing simulation

1. Normalize all geometry into one coordinate system and physical scale.
2. Reconstruct the intended stock / panel region.
3. Interpret each path using the source semantics and confirmed CAM mapping.
4. Convert each through-cut path to its physical cut sweep using the measured or explicitly assumed kerf.
5. Union all through-cut removal regions.
6. Subtract the union from the stock.
7. Identify all connected material components.
8. Classify every component as:
   - intended product body;
   - intentionally retained secondary part;
   - loose slug / internal island intended to fall out;
   - unintended detached island;
   - uncertain / needs operator decision.
9. Compare the resulting remaining material with the intended visual design and product assembly.

Do not infer the final part by counting black pixels, subpaths, contours or SVG objects before applying the actual cut operations.

### 5.2 Open cuts and closed loops have different outcomes

A closed through-cut loop can separate the enclosed slug from the surrounding panel. The slug may fall out while the surrounding panel remains one connected part. That is often an intended opening.

An open slot that ends inside the material may not detach anything. It may only create a slit.

A cut that reaches the panel perimeter can connect an internal region to outside scrap and may release a larger waste section.

A cut path that crosses the whole panel can split the stock into multiple parts.

Therefore, count both:
- connected components of the material remaining after cutting; and
- the identity / disposition of enclosed or edge-connected slugs.

The question is not merely “is there one black region?” It is “which physical component is the intended product, and what exactly will be released as waste?”

### 5.3 Count topology in the correct geometry

For a one-piece panel, the normal design objective is one intended connected product body after all planned cutouts have been removed. A product intentionally composed of multiple assembled pieces must declare those pieces and their joints.

Important caveats:

- A compound SVG path with many subpaths does not imply the same number of loose physical parts.
- A single compound path can contain many holes, nested contours or visual shapes.
- Fill-rule, direction, open/closed status, overlap and CAM operation all affect interpretation.
- A raster connected-component count is a diagnostic only; it can change with resolution, threshold, anti-aliasing and incorrect color semantics.
- A one-component result is not enough: a 0.2 mm neck can connect two regions digitally and still fail physically.

Use vector Boolean geometry as the primary analysis. Use high-resolution raster masks as a cross-check, not as the sole source of truth.

### 5.4 Evaluate the material connection graph

Build a structural graph for the intended product:

- Nodes: major retained material regions (outer frame, halo rim, face, veil, hands, sleeves, torso, base, tabs, etc.).
- Edges: actual material bridges connecting those regions.

For each bridge, record:
- nominal width;
- residual width after kerf and tolerances;
- length and orientation;
- local curvature / notch geometry;
- whether engraving passes through or weakens it;
- what other bridges remain if this one breaks.

A valid visual contact is not necessarily a physical connection. Confirm that the vector regions overlap or connect after actual cut geometry is applied.

---

## 6. Kerf, bridges and material tolerances

### 6.1 Calibrate kerf on the real process

Kerf depends on material formulation, thickness, density, moisture, focus, lens, power, speed, air assist, machine condition and CAM compensation.

Do not use a generic internet kerf value as the production value for MDF.

For every material / machine / settings combination that matters:

1. Use a coupon from the same supplier and preferably the same material batch.
2. Record actual thickness with a suitable measuring tool.
3. Cut a calibration pattern with slots, tabs and nested profiles.
4. Measure top and bottom kerf where relevant.
5. Compare nominal vector dimensions with measured finished dimensions.
6. Repeat enough times to understand variation.
7. Record the machine, lens, focus, air assist, power, speed, passes and material batch.
8. Update the CAM kerf value only from measured results.
9. Preserve the raw readings and date.

### 6.2 Bridge width is not the same as cut-line spacing

A bridge is material that remains between two cut boundaries. Parallel-line spacing is the gap between toolpaths. They are related but not interchangeable.

When two parallel centerline paths are separated by distance d and the kerf is symmetric k, a first-order residual web estimate is d − k. This is only an approximation; real geometry, compensation and process variation must be modeled.

Aalto’s guide recommends a 3 mm gap between parallel lines as a general design practice to reduce local heat concentration and damage. That is not a universal minimum bridge width, and it is not a guaranteed value for every machine or MDF formulation.

### 6.3 Use project targets as targets, not universal material laws

The BURVE brief suggested beginning with 4–5 mm or larger structural bridges for 6 mm MDF. Preserve this as an initial project design target only. It is not a universal MDF strength rule and it has not been proven on every machine, board brand, orientation or joint design.

A proposed bridge must pass:
- kerf-compensated geometric measurement;
- tolerance / worst-case residual-width assessment;
- local geometry review;
- physical coupon testing;
- handling and assembly test.

If the bridge target is not achievable, redesign the negative space or redistribute structural paths. Do not merely reduce the safety target without documenting why.

### 6.4 Erosion / tolerance stress tests

Run a digital robustness sweep using a set of small erosions or boundary perturbations to reveal narrow connections. Report the values tested and the components that split.

Interpret these as sensitivity tests, not as direct predictions of mechanical strength. A morphology operation does not model bending, impact, grain/fiber variability, heat damage, screw loads or assembly stress.

---

## 7. Design-specific structural rules

### 7.1 Faces and facial features

When the design brief requires an opaque face:

- Keep the entire face as retained stock material.
- Connect the face to the veil, hair, neck or main body.
- Represent eyes, eyebrows, nose, philtrum, lips and subtle expression lines as surface engraving.
- Never convert facial details into through-holes or isolated black islands.
- Inspect whether the face reads correctly at actual production size and with the intended finish.
- If a luminous face is desired, treat it as a different layered product design using an intentional aperture and diffuser; do not quietly violate the opaque-face specification.

### 7.2 Hands

- Keep palms, fingers, wrists, forearms and sleeves connected as one structural composition.
- Prefer engraved finger separations over narrow through-cut finger slots.
- Check the thumb and palm junction at actual scale.
- Avoid tiny isolated pieces between fingers.
- Verify that the prayer gesture remains recognizable after the engraving is reduced to the actual laser line width and burn contrast.

### 7.3 Halo / circular geometry

- A circular halo is an artistic symbol, not automatically a separate physical ring.
- Connect radial members to the intended rim and to the main retained structure where needed.
- Do not add a new outer hoop that conflicts with the actual panel perimeter or assembly geometry.
- Make sure each spoke ends in material that is truly connected, not merely touching in a visual preview.
- Keep enough material around the halo to survive the actual kerf and handling.

### 7.4 Hair, veil and garment

- Use large, intentional negative-space windows that follow the form.
- The black ribbons between windows are structural webs.
- Connect the veil to the face, shoulders and body where required.
- Avoid long isolated strips, acute tips, narrow necks and unconnected decorative folds.
- Prefer fewer broad and elegant windows over many microscopic cut lines, provided the visual identity remains intact.

### 7.5 Outer perimeter, tabs and product assembly

- Treat the panel outline as manufacturing geometry.
- Do not redraw, replace or decorate the panel perimeter without explicit design intent.
- Verify tabs, slots, seams, bottom seating curves, top openings and corner joints against the assembled product.
- For multi-face lanterns, each face must share the same controlled dimensional datum and assembly scheme.
- A design for one face is not yet a validated multi-face assembly.

---

## 8. Preserve a single geometry master

Every output must be derived from the same master geometry and version.

Required views / artifacts should be generated from one controlled source:

1. Front preview.
2. Material-retained mask.
3. Through-cut mask.
4. Face engraving layer.
5. Decorative engraving layer.
6. Combined cut + engraving view.
7. Connected-component / bridge diagnostic.
8. Illuminated render, if required.
9. SVG master.
10. DXF export, if supported by the geometry pipeline.
11. CAM operation map and manufacturing notes.

The render must not show a different design from the SVG or cut mask. The mask must not be manually redrawn independently of the vector. The face engraving must overlay the same face geometry used in the front preview.

If an image-generation model is used for concept exploration, its image is not a vector master and must never be described as a validated production file. Rebuild the approved design as vector geometry and re-run all checks.

---

## 9. Vector and CAM cleanup

Before export, verify:

- One documented physical unit system, preferably millimeters.
- Correct document dimensions and panel perimeter.
- All transforms are accounted for; flatten only when safe and preserve the original.
- Fonts are converted to paths or otherwise made portable.
- No hidden objects, unknown external references or unresolved linked files.
- No duplicate or coincident cut paths.
- No unnecessary self-intersections or ambiguous compound path winding.
- Open / closed path intent is explicit.
- Cut and engraving operations are in separate named layers.
- Line colors are mapped to documented operations for the exact CAM setup.
- No stroke width is being mistaken for kerf.
- Curves are smooth and node count is reasonable.
- DXF entities preserve intended curves / arcs as well as possible.
- Any raster preview is only a preview, not a substitute for vector geometry.
- Interior cuts are ordered before the outer panel boundary when appropriate to the machine / CAM workflow, so the panel remains registered during internal cutting. Confirm the exact order with the CAM operator.
- The exported file is reopened in the target CAM software and its interpreted operation list is inspected.

Do not assign laser speed or power without the machine specification and material test. No machine parameters were provided in the BURVE case, so no numerical production settings are inferable from that case.

---

## 10. Required analysis outputs for a future task

For a nontrivial laser-cut design, produce a report with these sections:

### A. Source and interpretation
- exact source file and revision/hash;
- dimensions and unit system;
- layer/object inventory;
- path types and fill rules;
- confirmed user/CAM operation mapping;
- assumptions and unresolved semantics.

### B. Physical model
- stock / finished panel outline;
- through-cut paths;
- engraving paths;
- kerf source and compensation status;
- actual cut-sweep model used;
- material remaining after Boolean subtraction.

### C. Topology
- intended product component count;
- all disconnected material components;
- all intended loose slugs / cutouts;
- unintended retained islands;
- bridges, residual widths and narrow necks;
- topology changes under tolerance/erosion tests.

### D. Visual and perceptual quality
- recognition at actual size;
- facial integrity and expression;
- hierarchy / focal point;
- negative-space balance;
- light path and shadow / diffusion intent;
- consistency between unlit and illuminated views.

### E. Manufacturing optimization
- number of cut loops / passes / toolpaths;
- total vector cut length;
- engraving length / area;
- duplicate paths and unnecessary nodes;
- estimated operation order;
- potential cut-length savings;
- which simplifications preserve or damage the design intent.

### F. Evidence and disposition
- checks run and exact settings;
- checks not run;
- remaining unknowns;
- physical coupon required;
- release status and stop conditions.

Do not invent machine time. Estimate it only from actual machine speed, path length, pierce count, operation order and acceleration / cornering assumptions. If those are unavailable, compare geometry and operation counts without a time claim.

---

## 11. Release ladder: do not overstate readiness

Use explicit stages:

1. **CONCEPT_ONLY** — image or sketch; no manufacturing semantics verified.
2. **VECTOR_PARSED** — exact file and objects parsed.
3. **OPERATIONS_CLASSIFIED** — cut, engrave, mark and reference paths mapped.
4. **TOPOLOGY_VERIFIED_DIGITALLY** — Boolean cut simulation and connected-component analysis completed.
5. **DIMENSIONALLY_VERIFIED** — scale, kerf model and bridge widths reviewed.
6. **CAM_REVIEWED** — exact output opened in the target CAM and operation mapping confirmed.
7. **COUPON_PASSED** — material/process coupon physically inspected.
8. **PROTOTYPE_PASSED** — full part cut, handled and assembled.
9. **PRODUCTION_APPROVED** — repeatable manufacturing and quality checks demonstrated.

A PNG is not a manufacturing file. An SVG/DXF that parses is not a CAM pass. A single connected raster region is not a strength test. A good prototype is not proof of batch-to-batch process capability.

---

## 12. BURVE case study: María, Luz que Acompaña

### Source provenance

This case was supplied directly by the Owner in the conversation:
- a BURVE product specification / design prompt for a decorative religious lantern;
- an original file named 1FarolPVirgen3.svg;
- an illuminated reference photograph of the Virgin Mary panel.

No separate peer-reviewed or technical article was uploaded as part of that particular case. The external technical references in this runbook were consulted independently and are cited below.

### Owner-confirmed rules for this case

- The panel is a trapezoidal lantern face, not a square plaque.
- The red paths in the supplied SVG identify the original face / boundary and cut geometry as explained by the Owner. They must be interpreted in the context of that file and not replaced by a new circular frame or decorative hoop.
- Black represents MDF that remains.
- White represents material removed by through-cutting.
- Blue represents surface engraving, not through-cutting.
- The face must remain opaque and physically continuous.
- Facial details must be engraved, not punched through.
- No loose black islands are acceptable unless explicitly designed as separate parts.
- The halo, veil, face, hands, garments and base must be evaluated after the cut operations, not just in the illustration.
- The visual front, binary mask, render and vector master must all represent the same geometry.
- The suggested 4–5 mm bridge width is an initial design target for the 6 mm MDF brief, not a validated universal minimum.

### Mistakes that must not be repeated

1. **Do not add an independent halo ring just because the picture contains a circular halo.** The red geometry defines the actual lantern-panel boundary / cut structure for this case. The halo must be designed inside that geometry.
2. **Do not treat a visually attractive generated illustration as a reconstructed SVG.** Image generation can suggest a style, but it does not preserve exact source paths, dimensions, assembly slots or topology.
3. **Do not equate black filled subpaths with actual pieces that remain.** First understand path fill/stroke, compound-path fill-rule, operation mapping and cut geometry. Then simulate the manufacturing subtraction.
4. **Do not treat white pixels as through-cuts unless they correspond to actual CAM cut paths.**
5. **Do not make eyes, eyebrows, nose, philtrum or lips into holes** when the face is specified to be opaque.
6. **Do not interpret apparent touching as physical connection.** Calculate the residual material bridge after kerf.
7. **Do not claim a connected structure solely from a low-resolution raster mask.** Recompute using vector Boolean geometry and cross-check at adequate resolution.
8. **Do not claim production readiness from the render.** The exact CAM file and a physical coupon/prototype remain separate gates.

### Important correction to prior analysis

Earlier visual/raster diagnostics in the conversation reported multiple black components. Those counts were not a validated manufacturing verdict because path semantics, the role of red paths, the actual stock boundary, cut sweeps and the resulting scrap regions had not all been reconciled into one Boolean manufacturing model.

Preserve those earlier counts as provisional observations only. Do not carry them forward as canonical geometry facts or use them as a reason to redesign the artwork without rechecking the actual vector operations.

### Best method for this case

1. Preserve and parse the exact original SVG.
2. Confirm the red paths' role and panel boundary with the Owner's explanation.
3. Preserve the trapezoidal panel datum.
4. Classify all internal through-cuts and engravings.
5. Make the opaque face an uninterrupted retained region.
6. Convert cut centerlines to kerf-aware cut sweeps.
7. Compute the remaining MDF, detached slugs and connected components.
8. Measure every critical bridge after kerf / tolerance allowance.
9. Review the halo, hair, veil, hands and base as actual connected material, not as a drawing.
10. Generate the preview, mask, engraving layers, SVG and DXF from one master.
11. Reopen in the target CAM and perform a same-batch MDF coupon before releasing a prototype.

---

## 13. MDF 6 mm research and process evidence

A directly relevant experimental paper is:

**Eltawahni, H. A., Olabi, A. G., & Benyounis, K. Y. (2011).** “Investigating the CO₂ laser cutting parameters of MDF wood composite material.” *Optics & Laser Technology*, 43(3), 648–659. DOI: 10.1016/j.optlastec.2010.09.006.  
https://doi.org/10.1016/j.optlastec.2010.09.006  
Repository record: https://doras.dcu.ie/18199/

The study tested MDF panels of 4, 6 and 9 mm and examined laser power, cutting speed, air pressure and focal-point position. Its quality measures included upper and lower kerf width, the upper/lower kerf ratio, cut-section roughness and operating cost. This directly supports the rule that MDF 6 mm settings and kerf must be measured / optimized for the real machine rather than assumed from another material or thickness.

An earlier study is:

**Lum, K. C. P., Ng, S. L., & Black, I. (2000).** “CO₂ laser cutting of MDF: 1. Determination of process parameter settings.” *Optics & Laser Technology*, 32(1), 67–76. DOI: 10.1016/S0030-3992(00)00020-7.  
https://doi.org/10.1016/S0030-3992(00)00020-7

Aalto University’s educational guide provides practical design context for kerf, separation between parallel cuts, material brittleness, vector cutting and engraving. Its 3 mm parallel-line gap is a general design recommendation, not a universal bridge-strength specification.  
https://digitaldesign.aalto.fi/digital-design-workflows/digital-production/laser-cutting/creating-a-design-for-laser-cutting/

The W3C SVG 2 specification is the authoritative source for fill, stroke, open-subpath fill closure and fill-rule semantics:  
https://www.w3.org/TR/SVG/latest/painting.html  
https://www.w3.org/TR/svg-paths/

Use primary standards and peer-reviewed process studies wherever available. Vendor design limits may be useful, but mark them as supplier-specific and do not universalize them.

---

## 14. How future AI sessions should activate and improve this skill

### When a new task arrives

1. Refresh the live repository route and current permissions using the IABV continuity method.
2. Retrieve this runbook when laser vector design / review / manufacturing is relevant.
3. Identify the exact file, material, thickness, machine, CAM and actual operation mapping available.
4. State what is known, inferred and unknown.
5. Apply the vector semantics → stock / operation model → kerf-aware Boolean simulation → topology / bridge validation sequence.
6. Produce the required report and a clear release stage.
7. Preserve meaningful new findings in a dated knowledge delta and update the skill only when evidence supports a real method improvement.
8. Fetch back the exact committed bytes and verify that cross-AI navigation points to the current version.

### Required questions when essential data is missing

Ask only for missing facts that materially alter the manufacturing result, for example:
- Which colors / layers map to through-cut, engraving and reference in the exact CAM?
- What is the actual material and measured thickness?
- What machine / lens / CAM profile and measured kerf are being used?
- Which regions are intended as product parts versus waste slugs?

If the user only wants concept art, do not block the creative work with machine questions. Label the result CONCEPT_ONLY and explain which manufacturing facts remain unknown.

### Do not claim automatic learning

This document is shared external memory. A future model can use it only if it retrieves the file through its available context / GitHub connector and actually applies the method. A new link, branch, commit or PR does not prove retrieval, application or causal reuse.

Use the IABV cross-AI activation states:
- MEMORY_RETRIEVED
- METHOD_ACTIVATED
- METHOD_APPLIED
- OUTCOME_VERIFIED
- LATER_CAUSAL_REUSE

Record the exact revision and the concrete decision changed. Runtime enforcement, automatic skill invocation and model-weight changes remain NOT_PROVEN unless separately implemented and measured.

---

## 15. Acceptance checklist

A future review must not be marked complete unless it records these answers:

- [ ] Exact source file and revision identified.
- [ ] Units, dimensions, transforms and panel outline verified.
- [ ] Fill/stroke, open/closed paths and compound fill-rules understood.
- [ ] CAM operation mapping confirmed; colors not guessed.
- [ ] Stock region and intended finished region defined.
- [ ] Kerf source / compensation status stated.
- [ ] Actual cut sweeps applied to stock geometry.
- [ ] Kept product components and dropped slugs classified.
- [ ] Unintended disconnected islands identified or ruled out.
- [ ] Critical residual bridges measured after kerf / tolerances.
- [ ] Engraving layers distinguished from through-cuts.
- [ ] Face / hands / other critical solid areas remain continuous where required.
- [ ] No duplicate or unintended paths.
- [ ] Front, mask, render and vectors derive from the same geometry master.
- [ ] SVG / DXF reopened in the target CAM.
- [ ] Machine settings come from measured process evidence, not guesses.
- [ ] Physical coupon / prototype state recorded.
- [ ] Release ladder stage declared honestly.

**Stop condition:** if path semantics, CAM mapping, stock boundary or the identity of retained regions cannot be resolved, do not call the file production-ready. Return a bounded list of unresolved decisions and keep the output at the appropriate earlier release stage.

