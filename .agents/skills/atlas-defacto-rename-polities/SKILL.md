---
name: atlas-defacto-rename-polities
description: Renames de facto polities for saves/atlas_defacto.naissance.
disable-model-invocation: true
---

## Step 1. Chunk out names for atlas_defacto.naissance.

1. Find atlas_defacto.naissance. This is structured as time-aware GeoJSON, with timestamps and geometry diffs. Note that only deltas are tracked, so it is important for you to avoid accidentally packing redundant changes.
2. Chunk out polity names to a temporary directory, `/temp_jobs/polity_names_<#>.txt`. Each chunk should contain 1024 polities at most, as a `<polity ID>: string` map.

## Step 2. Edit Polity Names.

1. All polity names are to follow the English formal name given to the polity (i.e. French Republic, not Third French Republic; United States of America, not USA). 
  1. If no formal name is found, the name may be preserved with any typos corrected. 
  2. Non-state actors and militant groups also often have formal names.
  3. Military occupations are to retain the suffix (Military Occupation).
2. Edit each chunk .txt file to follow the rules in Step 2.1.
3. For each chunk, verify each line to ensure that the formal name is historically correct. If you suspect a name is incorrect, you must state 'I HAVE FAILED MYSELF' and proceed to Step 2. Proceed to Step 3 otherwise.

## Step 3. Repackage properties back into atlas_defacto.naissance.

1. Re-package formal name chunks back into atlas_defacto.naissance, and bake the cache file so that the user can inspect the .naissance files and ensure that it is correct. Remember not to duplicate .name properties over multiple keyframes, keep diff architecture in mind.