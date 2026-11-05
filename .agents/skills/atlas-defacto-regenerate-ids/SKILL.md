---
name: atlas-defacto-regenerate-ids
description: Regenerates IDs for saves/atlas_defacto.naissance.
disable-model-invocation: true
---

The goal of this workflow is to regenerate polity IDs for `saves/atlas_defacto.naissance` such that the IDs are in chronological-alphabetical order of appearance, starting with ID: 1. If two or more polities appear on the same day, the IDs should be numbered alphabetically by increasing order.

Multiple file paths across different projects need to be changed to ensure compatibility.

Properties to change: `.id`, `.state_id`; the key of the GeometryPolygon is the same as the `.id`. This may change; you will have to define for yourself which ID properties merit changing to keep in line with this directive.

## Step 1. Check file paths.

1. F:/Active Projects/Project 1436 - Dataview/ has a preserved tests/capitals/chunks/ folder in which individual state_id brackets must map onto the new IDs as generated, as part of Stadestér.
2. /saves/atlas_defacto.naissance contains the savefile you are looking to change the ID of each polities for.

## Step 2. Regenerate IDs.

1. Write a NodeJS script in /temp_jobs/ to regenerate the IDs for `saves/atlas_defacto.naissance` and associated filepaths as specified.
2. Execute the NodeJS script.
3. Ensure that capital cities are correctly packed in Dataview.

## Step 3. Ensure Stadestér alignment.

1. Check your IDs for `saves/atlas_defacto.naissance` to ensure that they appear correct.
2. Check that Stadestér capitals in F:/Active Projects/Project 1436 - Dataview/ map on correctly.