"""Validate this state checkpoint; no application runtime tests."""
from pathlib import Path
import subprocess, json, re, hashlib, platform
from urllib.parse import urlsplit, unquote

root = Path(__file__).resolve().parents[3]
base = "1bc84a44e6aacb3a436f7f99a203b6e43dbfbe59"
candidate = "634da4224f15dd6a5a4e9010fe1811dec8c7954d"
evdir = Path(__file__).resolve().parent
checks = []

def run(args):
    p = subprocess.run(args, cwd=root, capture_output=True, text=True)
    assert p.returncode == 0, (args, p.returncode, p.stderr, p.stdout)
    return p.stdout

def record(name, detail):
    checks.append({"check": name, "result": "PASS", "detail": detail})

state = json.loads((evdir / "remote-state.json").read_text())
record("protected source/config delta", run([
    "git", "diff", "--exit-code", candidate, base, "--", ".",
    ":!report", ":!task", ":!docs/progress.md"]))
record("candidate is decision ancestor", run([
    "git", "merge-base", "--is-ancestor", candidate, base]))
refs = dict(line.split(" ", 1) for line in run([
    "git", "for-each-ref", "--format=%(refname:strip=3) %(objectname)",
    "refs/remotes/origin"]).splitlines() if not line.startswith("HEAD "))
assert refs == {x["name"]: x["sha"] for x in state["branches"]}
record("Git refs match connector inventory", {"branches": len(refs)})
old = {line.split()[1].removeprefix("refs/heads/"): line.split()[0]
       for line in (root / "report/controller-evidence/20261115T065656Z-pa006-resume/remote-heads.txt").read_text().splitlines()}
assert old.keys() == refs.keys()
changed = {k: {"prior": old[k], "current": refs[k]}
           for k in refs if old[k] != refs[k]}
assert set(changed) == {"review/0010-pa006-controller-r4-20261115"}
record("prior branch-head comparison", {"unchanged": 24, "changed": changed})
packet = "task/0010-pa006-idempotency.md"
prior = run(["git", "show", base + ":" + packet])
current = (root / packet).read_text()
marker = "\n\nMulai dari "
assert current.split(marker, 1)[1] == prior.split(marker, 1)[1]
row = next(l + "\n" for l in current.splitlines()
           if l.startswith("| Latest state verification |"))
assert current.replace(row, "") == prior
record("original packet preserved except one metadata row",
       {"body_sha256": hashlib.sha256(prior.split(marker, 1)[1].encode()).hexdigest()})
paths = set(run(["git", "diff", "--name-only", base]).splitlines())
paths |= set(run(["git", "ls-files", "--others", "--exclude-standard"]).splitlines())
paths |= {str((evdir / n).relative_to(root)) for n in ["checks.json", "docs.log"]}
assert all(p.startswith("report/") or p in {packet, "docs/progress.md"} for p in paths)
assert [p.name for p in (root / "task").glob("0010*")] == ["0010-pa006-idempotency.md"]
record("record-only scope and one unfinished packet", sorted(paths))
count = 0
for name in paths:
    if not name.endswith(".md"):
        continue
    content = re.sub(r"```.*?```", "", (root / name).read_text(), flags=re.S)
    for target in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)(?:\s+"[^"]*")?\)', content):
        parts = urlsplit(unquote(target.strip("<>")))
        if parts.scheme or parts.netloc or not parts.path:
            continue
        dest = ((root / name).parent / parts.path).resolve()
        assert dest.is_relative_to(root), (name, target)
        # This command generates its own referenced output below.
        assert dest.exists() or dest == evdir / "checks.json", (name, target)
        count += 1
record("changed Markdown relative targets", {"links": count})
p = subprocess.run(["python3", "docs/tools/check_docs.py"], cwd=root,
                   capture_output=True, text=True)
(evdir / "docs.log").write_text(p.stdout + p.stderr)
assert p.returncode == 0, p.stderr
record("python3 docs/tools/check_docs.py", {"exit": p.returncode, **json.loads(p.stdout)})
record("git diff --check HEAD", run(["git", "diff", "--check", "HEAD"]))
output = {
    "result": "PASS",
    "scope": "state and review records only",
    "command": "python3 " + str(Path(__file__).relative_to(root)),
    "environment": {"python": platform.python_version(), "git": run(["git", "--version"]).strip()},
    "checks": checks,
    "runtime_acceptance_tests_executed_locally": 0,
    "qa_note": "Initial validation preceded generation of checks.json and reported its pending link; output generation is now ordered and verified. No application test ran."
}
(evdir / "checks.json").write_text(json.dumps(output, indent=2) + "\n")
assert json.loads((evdir / "checks.json").read_text())["result"] == "PASS"
print(json.dumps({"result": "PASS", "checks": len(checks), "links": count,
                  "protected_delta": [], "original_packet_preserved": True,
                  "docs": json.loads(p.stdout)}, indent=2))
