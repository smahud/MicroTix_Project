"""Read-only repository/record checks for the task0020 controller resume."""
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
MAIN = "41d1f33f16508491a34f66b767830b9dd3e5954e"
CANDIDATE = "bd37c14e6c41339a8743b3d4b723ee74f13bef08"
TESTED = "7118cce0db330acb02be0b3b774b1b1628d55d7a"
DECISION = "43043be4b0562f982316593cf6ef4e5d5b6951a6"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def record_only(path):
    return path.startswith(("report/", "task/")) or path == "docs/progress.md"


snapshot = json.loads((EVIDENCE / "remote-state.json").read_text())
refs = dict(line.split(" ", 1) for line in git(
    "for-each-ref", "--format=%(refname:strip=3) %(objectname)", "refs/remotes/origin"
).splitlines() if not line.startswith("HEAD "))
assert refs == {item["name"]: item["sha"] for item in snapshot["branches"]}
assert refs["main"] == MAIN
assert refs["session/2026-11-17-0020-job-lifecycle-authority"] == CANDIDATE
assert refs["review/0020-controller-20261117"] == DECISION
inventory = []
for branch, sha in sorted(refs.items()):
    paths = git("ls-tree", "-r", "--name-only", sha, "task/").splitlines()
    assert not any(path.startswith("task/0030-") for path in paths)
    assert all(path.split("/")[-1][:4] in {"0000", "0010", "0020"} for path in paths)
    reports = git("ls-tree", "-r", "--name-only", sha, "report/controller/", "report/orchestrator/", "report/reviewer/").splitlines()
    inventory.append({"branch": branch, "sha": sha, "tasks": paths,
                      "task0020_reports": [p for p in reports if "0020" in p]})

comparisons = []
for base, head in [(TESTED, CANDIDATE), (CANDIDATE, DECISION)]:
    subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=ROOT, check=True)
    changed = git("diff", "--name-only", base, head).splitlines()
    assert all(record_only(path) for path in changed), changed
    comparisons.append({"base": base, "head": head, "ancestor": True,
                        "changed_paths": changed, "application_config_delta_empty": True})

packet = (ROOT / "task/0020-job-lifecycle-authority.md").read_text()
assert "changes_requested" in packet and "`ready`" in packet
assert not (ROOT / "task/0020-job-lifecycle-authority_done.md").exists()
for idx in range(1, 10):
    assert f"REV-1711-{idx:02}" in packet
summary = json.loads((ROOT / "report/controller-evidence/20261117T134100Z-0020-review/review-results.json").read_text())
assert summary["candidate_sha"] == CANDIDATE
assert summary["verdict"] == "changes_requested"
assert summary["root_focused_probes"]["failed_assertions"] == 11
assert summary["root_focused_probes"]["errors"] == 0
assert summary["next_actor"] == "coding_agent"
assert "accepted" in (ROOT / "task/0010-pa006-idempotency_done.md").read_text()

for ci in snapshot["ci"]:
    assert ci["total"] == 3
    assert {c["name"] for c in ci["checks"]} == {"backend", "frontend", "docs"}
    assert all(c["head_sha"] == ci["sha"] and c["status"] == "completed" and
               c["conclusion"] == "success" for c in ci["checks"])

result = {"result": "PASS", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
          "python": platform.python_version(), "git": git("--version"),
          "branches": len(refs), "open_prs": len(snapshot["open_prs"]),
          "correction_delivery": "not_submitted", "task_execution": "ready",
          "task_review": "changes_requested", "next_actor": "coding_agent",
          "local_branch_inventories": inventory, "comparisons": comparisons,
          "ci": "Existing exact main/candidate/decision success3/3; not this checkpoint's CI",
          "application_runtime_tests_executed": 0,
          "prior_failures": "R1 historical 11 failed acceptance assertions/0 harness errors; not rerun"}
(EVIDENCE / "local-checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ["result", "observed_at_utc", "branches", "open_prs", "correction_delivery", "task_execution", "task_review", "next_actor", "application_runtime_tests_executed"]}, indent=2))
