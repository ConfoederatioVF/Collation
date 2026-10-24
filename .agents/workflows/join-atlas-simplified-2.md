---
description: Joins Seshat-compatible atlas_simplified.naissance with CShapes-2.0 and CShapes-Europe.
---

atlas_simplified.naissance currently needs to be joined with CShapes-2.0. The way this should work is that: 

STEP 1.
1. Spatiotemporally merge CShapes-Europe.geojson into atlas_simplified.naissance. This would apply from 1816-1886 only; it would not apply afterwards or beforehand. Make sure that each continuous polity in CShapes-Europe has its valid Seshat ID assigned to it.
2. Ensure topology; we do not want to be seeing stray polygons from the original atlas_simplified.naissance within Europe itself. At the same time, polities outside of Europe should be preserved, including, very often, the same polity (i.e. British Empire may still exist overseas, but not in the UK). Use scanline rasterisation to test for this guarantee.
3. CShapes-Europe should spatially inherit the colours from atlas.naissance via pole of inaccessibility.

STEP 2.

1. Each CShapes-2.0 polity must be assigned a valid Seshat ID. This should be done by dumping out the .txt and chunking out valid Seshat IDs via manual enrichment (do not use heuristics for this, they are famously flawed, do not use scripts, do not use semantics, only file read/write at this stage).
2. CShapes-2.0 should spatially inherit the colours from atlas.naissance via pole of inaccessibility.
3. After 1886AD, polities should switch directly to CShapes-2.0.

STEP 3. 

1. Ensure that each CShapes polity has a valid Correlates of War code. This can be populated correctly via R calls.

Sane-check your properties output for atlas_simplified.naissance. If it is not correct, you must state 'I HAVE FAILED MYSELF', and proceed to STEP 1.