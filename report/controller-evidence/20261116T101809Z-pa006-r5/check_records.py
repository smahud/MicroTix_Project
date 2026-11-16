"""Verify controller record consistency without changing application contents."""
from pathlib import Path
import json
import re
import subprocess

r = Path(__file__).resolve().parents[3]
paths = [r / "task/0010-pa006-idempotency_done.md", r / "report/LATEST_HANDOFF.md",
         r / "docs/progress.md", r / "report/controller/20261116T101809Z-0010-pa006-r5-review.md"]
paths.extend((r / "report/reviewer").glob("20261116T101809Z*.md"))
bad = []
total = 0
for p in paths:
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", p.read_text()):
        target = match.group(1).split("#")[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        total += 1
        if not (p.parent / target).resolve().exists():
            bad.append({"file": str(p.relative_to(r)), "target": target})
protected = ["backend", "apps", "instalasi.sh", ".github", "locales", "CONTRACT.md",
             "AGENTS.md", "docs/manifest.json", "docs/defaults.json"]
delta = subprocess.check_output(["git", "diff", "--name-only", "a301a94", "--", *protected], cwd=r, text=True).splitlines()
old = subprocess.check_output(["git", "show", "a301a94:task/0010-pa006-idempotency_done.md"], cwd=r, text=True)
new = (r / "task/0010-pa006-idempotency_done.md").read_text()
blocks = {}
for heading in ["Tujuan dan bukti masalah", "Scope dan ownership", "Pekerjaan wajib",
                "Acceptance yang wajib dibuktikan", "Verifikasi dan review"]:
    def block(text):
        start = text.index("## " + heading + "\n")
        end = text.find("\n## ", start + 1)
        return text[start:end if end != -1 else len(text)]
    blocks[heading] = block(old) == block(new)
result = {"relative_links_checked": total, "broken_links": bad, "protected_delta": delta,
          "original_task_blocks_unchanged": blocks,
          "task_files": sorted(p.name for p in (r / "task").glob("*.md"))}
Path(__file__).with_name("record-checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
assert not bad and not delta and all(blocks.values())
assert result["task_files"] == ["0000-start-here.md", "0010-pa006-idempotency_done.md"]
