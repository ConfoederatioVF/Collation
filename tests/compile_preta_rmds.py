import pathlib
import subprocess

import fitz

rscript = r"C:\Program Files\R\R-4.6.1\bin\x64\Rscript.exe"
root = pathlib.Path("histmap/1.data_raw/population_regional/PRETA").resolve()
targets = [
    "1.pre_columbian/6.bolivian_highlands/bolivian_highlands_literature_review.Rmd",
    "2.colonial/5.colonial_upper_peru_charcas/colonial_upper_peru_charcas_literature_review.Rmd",
]

for rel in targets:
  p = root / rel
  expr = f"rmarkdown::render('{p.name}', output_format='pdf_document', quiet=TRUE)"
  res = subprocess.run([rscript, "-e", expr], cwd=str(p.parent), capture_output=True, text=True)
  print(p.name, "RC=", res.returncode, flush=True)
  if res.returncode != 0:
    print((res.stdout + "\n" + res.stderr)[-1200:], flush=True)
    raise SystemExit(1)

out_dir = pathlib.Path("tests/preta_pdf_qa")
out_dir.mkdir(parents=True, exist_ok=True)
for nm, rel in [
    ("bolhi_p1.png", "1.pre_columbian/6.bolivian_highlands/bolivian_highlands_literature_review.pdf"),
    ("charcas_p1.png", "2.colonial/5.colonial_upper_peru_charcas/colonial_upper_peru_charcas_literature_review.pdf"),
]:
  doc = fitz.open(str(root / rel))
  doc[0].get_pixmap(dpi=150).save(str(out_dir / nm))
  print("Rendered", nm, "pages=", len(doc), flush=True)
