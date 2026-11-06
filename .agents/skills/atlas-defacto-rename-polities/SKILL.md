---
name: atlas-defacto-rename-polities
description: Renames de facto polities for saves/atlas_defacto.naissance.
disable-model-invocation: true
---

IMPORTANT. It is possible for this skill to have already been called. In such cases, it is typically because the skill has failed, and certain elements are in need of fixing.

## Step 1. Chunk out names for atlas_defacto.naissance.

1. Find atlas_defacto.naissance. This is structured as time-aware GeoJSON, with timestamps and geometry diffs. Note that only deltas are tracked, so it is important for you to avoid accidentally packing redundant changes.
2. Chunk out polity names to a temporary directory, `/temp_jobs/polity_names_<#>.txt`. Each chunk should contain 1024 polities at most, as a `<polity ID>: string` map.

## Step 2. Edit Polity Names.

1. All polity names are to follow the English formal name given to the polity (i.e. French Republic, not Third French Republic; United States of America, not USA). 
  1. If no formal name is found, the name may be preserved with any typos corrected. 
  2. Non-state actors and militant groups also often have formal names.
  3. Military occupations are to retain the suffix (Military Occupation). Note that the name of the Military Occupation should be contemporaneously accurate according to the government in power at the time, i.e. German Empire (Military Occupation), later German Reich (Military Occupation). Learn how to use diff keyframes to accomplish this task.
  4. Contemporaneous territorial designations or polygons with duplicate names likely require disambiguation. For instance, Habsburg Domains inside and outside the Holy Roman Empire comprise separate polygons and should have names disambiguating them as such, i.e. Habsburg Domains (within the HRE), Habsburg Domains (outside the HRE).
2. Edit each chunk .txt file to follow the rules in Step 2.1.
3. For each chunk, verify each line to ensure that the formal name is historically correct. If you suspect a name is incorrect, you must state 'I HAVE FAILED MYSELF' and proceed to Step 2. Proceed to Step 3 otherwise.

## Step 3. Repackage properties back into atlas_defacto.naissance.

1. Re-package formal name chunks back into atlas_defacto.naissance, and bake the cache file so that the user can inspect the .naissance files and ensure that it is correct. Remember not to duplicate .name properties over multiple keyframes, keep diff architecture in mind.