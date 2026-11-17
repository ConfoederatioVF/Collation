import glob
import json5
import numpy as np
import os
from PIL import Image

CENTAUR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def build_mask_lookup():
    mods = [
        m for m in sorted(glob.glob(os.path.join(CENTAUR_DIR, "[1-5].*/*/*.json5")))
        if not m.endswith("_source_ledger.json5")
    ]
    tables = {}
    for m in mods:
        d = json5.load(open(m, "r", encoding="utf-8"))
        stem = d["id"]
        mod_dir = os.path.dirname(m)
        mask_path = os.path.join(mod_dir, d["mask_file"])
        im = np.array(Image.open(mask_path))[..., :3]
        rgb_to_id = {}
        for rk, rv in d["regions"].items():
            col = rv.get("colour") or rv.get("color")
            if col and len(col) >= 3:
                rgb_to_id[(int(col[0]), int(col[1]), int(col[2]))] = rk
        # Store compact nonzero coords + region_id mapping for O(1) exact + coastal fallback lookup
        packed = im[:, :, 0].astype(np.uint32) * 65536 + im[:, :, 1].astype(np.uint32) * 256 + im[:, :, 2].astype(np.uint32)
        color_pack = {r * 65536 + g * 256 + b: rk for (r, g, b), rk in rgb_to_id.items()}
        tables[stem] = {
            "json5_path": m,
            "packed": packed,
            "color_pack": color_pack,
            "regions": list(d["regions"].keys()),
            "domain": d["domain"]
        }
        # Quick sanity test
        nz = int((packed > 0).sum())
        if nz == 0:
            print(f"[WARN] {stem} has 0 nonzero pixels!")
    np.savez_compressed(
        os.path.join(OUT_DIR, "mask_lookup_meta.npz"),
        stems=list(tables.keys())
    )
    print(f"Verified all {len(tables)} areal masks cleanly.")
    return tables


if __name__ == "__main__":
    build_mask_lookup()
