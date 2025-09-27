#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, subprocess, re

OUTDIR = Path("docs")
OUTDIR.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
outfile = OUTDIR / f"inventory_{stamp}.md"

def run(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()

def section(title, body):
    with open(outfile, "a", encoding="utf-8") as f:
        f.write(f"\n## {title}\n\n{body}\n")

# encabezado
with open(outfile, "w", encoding="utf-8") as f:
    f.write(f"# Inventory snapshot — {stamp}\n")
    f.write("_Modo El Colgado: vista invertida del repo antes del refactor._\n")

# 1) Estructura (2 niveles)
paths = []
for p in Path(".").glob("*"):
    if p.name == ".git": 
        continue
    paths.append(p)
body = "```\n"
for p in sorted(paths, key=lambda x: x.name.lower()):
    body += f"{p}\n"
    if p.is_dir():
        for q in sorted(p.glob("*")):
            if ".git" in q.parts: 
                continue
            body += f"  {q}\n"
body += "```\n"
section("Estructura (2 niveles)", body)

# 2) Archivos top-level
top_files = [p for p in Path(".").iterdir() if p.is_file() and p.name != ".git"]
body = "```\n" + "\n".join(sorted([f.name for f in top_files])) + "\n```\n"
section("Archivos top-level", body)

# 3) Notebooks
nbs = sorted(Path(".").rglob("*.ipynb"))
body = "```\n" + "\n".join(str(p) for p in nbs) + ("\n" if nbs else "\n(no hay)\n") + "```\n"
section("Notebooks (.ipynb)", body)

# 4) Scripts huérfanos en scripts/ (sin shebang)
body = "```\n"
scripts_dir = Path("scripts")
if scripts_dir.exists():
    orphan = []
    for p in sorted(scripts_dir.glob("*")):
        if p.is_file():
            try:
                first = p.open("r", encoding="utf-8", errors="ignore").readline()
            except Exception:
                first = ""
            if not first.startswith("#!"):
                orphan.append(str(p))
    body += "\n".join(orphan) if orphan else "(ninguno)"
else:
    body += "No existe carpeta scripts/"
body += "\n```\n"
section("Scripts potencialmente huérfanos (sin shebang en scripts/)", body)

# 5) Archivos >10MB
big = []
for p in Path(".").rglob("*"):
    if p.is_file() and ".git" not in p.parts:
        try:
            if p.stat().st_size > 10 * 1024 * 1024:
                big.append((p.stat().st_size, str(p)))
        except FileNotFoundError:
            pass
big.sort()
body = "```\n" + "\n".join(f"{sz/1e6:.1f} MB  {path}" for sz, path in big) + ("\n" if big else "\n(none)\n") + "```\n"
section("Archivos >10MB (working tree)", body)

# 6) Conteo de datos/figuras
exts = ["csv","tsv","parquet","feather","npy","png","jpg","jpeg","svg","pdf"]
rows = []
for ext in exts:
    cnt = sum(1 for _ in Path(".").rglob(f"*.{ext}") if ".git" not in _.parts)
    rows.append(f"{ext:8s} : {cnt}")
body = "```\n" + "\n".join(rows) + "\n```\n"
section("Conteo de archivos de datos y figuras", body)

# 7) Git LFS
lfs = run("git lfs env && git lfs ls-files || true")
section("Git LFS (si aplica)", f"```\n{lfs or 'git-lfs no instalado/configurado'}\n```")

# 8) Heurística de secretos
grep_patterns = r"(AWS|AKIA[0-9A-Z]{16}|SECRET|TOKEN|PASSWORD|PASS=|PRIVATE KEY|BEGIN RSA|BEGIN EC)"
hits = []
for p in Path(".").rglob("*"):
    if p.is_file() and ".git" not in p.parts and p.suffix not in {".png",".jpg",".jpeg",".pdf",".svg",".parquet",".feather",".npy"}:
        try:
            txt = p.read_text(errors="ignore")
            if re.search(grep_patterns, txt):
                hits.append(str(p))
        except Exception:
            pass
body = "```\n" + ("\n".join(hits) if hits else "(sin hallazgos)") + "\n```\n"
section("Búsqueda heurística de secretos", body)

# 9) Estadísticas del repo
stats = []
stats.append("Commits totales:\n" + run("git rev-list --count HEAD"))
stats.append("\nAutores:\n" + run("git shortlog -sn"))
stats.append("\nRamas locales:\n" + run("git branch --format='%(refname:short)'"))
section("Estadísticas rápidas", "```\n" + "\n".join(stats) + "\n```")

print(f"✅ Inventario generado en {outfile}")
