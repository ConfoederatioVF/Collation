---
name: atlas-defacto-regenerate-descriptions
description: Regenerates descriptions to be more in line with their `.link` fields.
disable-model-invocation: true
---

## Step 1. Chunk out descriptions for atlas_defacto.naissance.

1. Find atlas_defacto.naissance. This is structured as time-aware GeoJSON, with timestamps and geometry diffs. Note that only deltas are tracked, so it is important for you to avoid accidentally packing redundant changes.
2. Chunk out polity descriptions to a temporary directory, `/temp_jobs/polity_descriptions_<#>.txt`. Each chunk should contain 512 polities at most, as a `<polity ID>: string` map.

## Step 2. Edit Polity `.description` fields.

1. Check the `.link` of each polity entry, and form a brief description based off the Wikipedia summary. In addition, the contents of the infobox should be formatted as tags following a double line break `\n\n` at the end of the description.
2. Because this will take a lot of tokens, any subagents should use Gemini 3.8 Flash if possible instead of Gemini 4 Argon.

Example format:
```
French Fifth Republic. Semi-presidential government formed in 1958 which succeeded the French Fourth Republic. In the 1960s, most of its colonies gained independence, with continued influence in the Francafrique.

Capital and largest city: Paris (de facto); Official languages: French; Common languages: French and other regional languages; ...
```

## Step 3. Repackage properties back into atlas_defacto.naissance.

1. Re-package `.description` fields back into atlas_defacto.naissance, and bake the cache file so that the user can inspect the .naissance files and ensure that it is correct. Remember not to duplicate `.description` properties over multiple keyframes, keep diff architecture in mind.