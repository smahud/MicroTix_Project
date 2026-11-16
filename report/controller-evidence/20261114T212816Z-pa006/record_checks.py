"""Check records-only review scope, original acceptance and local links."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
BASE = "9e9bf2d42002a00a69d54fc355b77384897b9478"
changed = subprocess.check_output(["git", "diff", "--cached", "--name-only", BASE], text=True).splitlines()
assert changed, "stage intended review records before checking"
allowed = lambda p: p.startswith("report/") or p == "docs/progress.md" or p in (
    "task/0010-pa006-idempotency.md", "task/0010-pa006-idempotency_done.md",
)
assert all(allowed(p) for p in changed), "application/config/schema/product scope changed"
original = subprocess.check_output(["git", "show", f"{BASE}:task/0010-pa006-idempotency_done.md"], text=True)
current = (ROOT / "task/0010-pa006-idempotency.md").read_text()
for start, end in (
    ("## Tujuan dan bukti masalah", "## Scope dan ownership"),
    ("## Pekerjaan wajib", "## Verifikasi dan review"),
    ("## Verifikasi dan review", "## Penyerahan dan batas selesai"),
):
    assert original[original.index(start):original.index(end)] == current[current.index(start):current.index(end)], start
assert "| Execution status | `ready`" in current
assert "| Review status | `changes_requested`" in current
assert "| Next actor | **coding_agent**" in current
assert not (ROOT / "task/0010-pa006-idempotency_done.md").exists()
links = 0
files = 0
for name in changed:
    p = ROOT / name
    if not p.is_file() or p.suffix != ".md":
        continue
    files += 1
    for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", p.read_text()):
        target = target.split("#", 1)[0].strip("<>")
        if not target or re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue
        assert (p.parent / target).exists(), f"broken link {name}: {target}"
        links += 1
    assert not re.search(r"github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9]{30,}", p.read_text()), "credential-like text"
subprocess.run(["git", "diff", "--cached", "--check"], check=True)
subprocess.run(["git", "diff", "--quiet", BASE, "--", "backend", "apps", ".github", "instalasi.sh", "CONTRACT.md", "docs/repository-manifest.json"], check=True)
print(json.dumps({"result": "PASS", "changed_paths": len(changed), "markdown_files": files, "local_links": links, "original_objective_work_acceptance_verification": "byte-identical", "application_config_contract_manifest_delta": "empty"}, indent=2))
