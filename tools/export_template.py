#!/usr/bin/env python3
"""Export the content store engine as an empty template repo: scripts, tn-cstore skills, user guide.
Leaves out everything that belongs to this vault: articles, notes, data files, para.py, descriptions.py, LOCAL.md.
  export_template.py <dest>   dest must not exist or be empty; init.py then sets up the empty store there
The template is ready for `/tn-cstore-init`. Re-export after engine changes to update it."""
import sys, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

ENGINE = ["tools/init.py", "tools/ingest.py", "tools/fetch.py", "tools/images.py", "tools/link.py", "tools/check.py",
          "tools/export_template.py", "tools/requirements.txt", "docs/tn-cstore-user-guide.md", "00_Staging/articles/README.md"]
VAULT_ONLY = {"LOCAL.md"}   # per-vault decisions inside the skills folder

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    dest = Path(sys.argv[1]).resolve()
    if dest == ROOT or ROOT in dest.parents: sys.exit("dest must be outside this repo")
    if dest.exists() and any(p.name != ".git" for p in dest.iterdir()): sys.exit(f"{dest} is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    for rel in ENGINE:
        src, out = ROOT / rel, dest / rel
        if not src.exists(): sys.exit(f"missing {rel}")
        out.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, out)
    for skill in sorted((ROOT / ".claude/skills").glob("tn-cstore*")):
        shutil.copytree(skill, dest / ".claude/skills" / skill.name, ignore=lambda d, names: [n for n in names if n in VAULT_ONLY or n == "__pycache__"])
    subprocess.run([sys.executable, str(dest / "tools/init.py")], check=True)
    n = sum(1 for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts)
    print(f"template exported to {dest} ({n} files). Next: git init/commit/push, then /tn-cstore-init in the new repo.")

if __name__ == "__main__":
    main()
