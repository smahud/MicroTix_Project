#!/usr/bin/env python3
"""Independent pure-Python grammar probe for task0010 / PA006 PR24.

Run from any directory: python3 /path/to/grammar_probe.py
Writes grammar-summary.json beside this file. No Django/DB imports and no
repository mutation beyond that result file. Source parser is AST-extracted
verbatim from the current checkout; baseline call-sites are read by git show.
"""

from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[3]
BASELINE = "9903d9b0cf09d737b553da3c21067b4810e956c0"
CANDIDATE = "a301a94c2b3268679065e85bbef66f35949483f7"
SOURCE = "backend/domains/jobs/migrations/0004_idempotency_identity.py"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main() -> None:
    tree = ast.parse((ROOT / SOURCE).read_text())
    body = []
    keep = {"_canonical_uuid", "_split_legacy_scope", "AmbiguousLegacyScope"}
    constants = {"_PLATFORM_LITERAL", "_OPAQUE_RESOURCE_OPERATIONS"}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in keep:
            body.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constants
            for target in node.targets
        ):
            body.append(node)
    namespace = {"_uuid": uuid}
    exec(compile(ast.Module(body=body, type_ignores=[]), "<candidate-ast>", "exec"), namespace)
    rng = random.Random(16112026)

    def spellings(value: str) -> list[str]:
        raw_hex = uuid.UUID(value).hex
        samples = {
            value, value.upper(), raw_hex, "{" + value + "}",
            "urn:uuid:" + value, "uuid:" + value, "urn:" + value,
            "{{" + value + "}}", "+" + raw_hex[1:],
            "\u0660" + raw_hex[1:], raw_hex[:12] + "_" + raw_hex[13:],
        }
        for _ in range(500):
            text = rng.choice([value, raw_hex, value.upper()])
            for _ in range(rng.randrange(1, 7)):
                position = rng.randrange(len(text) + 1)
                text = text[:position] + rng.choice(["urn:", "uuid:", "-"]) + text[position:]
            if rng.choice([False, True]):
                text = "{" + text + "}"
            samples.add(text)
        accepted = []
        for text in sorted(samples):
            try:
                uuid.UUID(text)
            except (ValueError, TypeError, AttributeError):
                continue
            accepted.append(text)
        return accepted

    first = "abcdef12-2345-6789-abcd-ef1234567890"
    second = "fedcba98-7654-3210-abcd-ef1234567890"
    tenants, resources = spellings(first), spellings(second)
    counts = {"pairs": 0, "valid_scopes": 0, "uuid": 0, "empty": 0, "opaque": 0, "platform": 0}
    mismatches = []
    split = namespace["_split_legacy_scope"]
    for tenant, resource in itertools.product(tenants, resources):
        for operation, raw in [
            ("router_backup", resource), ("payment_submission", ""),
            ("identity_conflict_resolve", "aB0f1234:opaque"),
        ]:
            scope = f"{operation}:{tenant}:{raw}"
            if len(scope) > 256:
                continue
            counts["valid_scopes"] += 1
            try:
                parts = split(scope)
            except Exception as exc:
                mismatches.append((scope, str(exc)))
                continue
            if parts != (operation, tenant, raw):
                mismatches.append((scope, parts))
            counts["uuid" if raw == resource else "empty" if raw == "" else "opaque"] += 1
        counts["pairs"] += 1

    for resource in resources:
        scope = f"platform_submission_approve:platform:{resource}"
        assert split(scope) == ("platform_submission_approve", "platform", resource)
        counts["platform"] += 1
    for bad in [
        "", None, "op:PLATFORM:" + first, "op:bad:" + first,
        "op:" + first + ":garbage", "op:" + first,
    ]:
        assert split(bad) is None
    try:
        split("op:a:b:c", tenant_valid=lambda value: True, resource_valid=lambda value: True)
    except namespace["AmbiguousLegacyScope"]:
        pass
    else:
        raise AssertionError("ambiguous injection did not stop")

    callsites = []
    paths = git("ls-tree", "-r", "--name-only", BASELINE, "backend/domains").splitlines()
    for path in paths:
        if not path.endswith(".py"):
            continue
        source = git("show", f"{BASELINE}:{path}")
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "idempotent"
                ):
                    callsites.append({
                        "path": path, "line": decorator.lineno,
                        "operation": ast.literal_eval(decorator.args[0]),
                        "decorator": ast.get_source_segment(source, decorator),
                    })

    summary = {
        "python": sys.version.split()[0], "seed": 16112026,
        "inspected_candidate": CANDIDATE, "baseline_writer": BASELINE,
        "parser_source": SOURCE,
        "parser_blob_sha": git("hash-object", SOURCE).strip(),
        "tenant_spellings": len(tenants), "resource_spellings": len(resources),
        "counts": counts, "mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:3], "malformed_cases_passed": 6,
        "injected_ambiguity_passed": True,
        "baseline_callsite_count": len(callsites), "baseline_callsites": callsites,
        "limits": "Pure Python and source inventory only; no DB, HTTP, filesystem effects, CI or deployment verification.",
    }
    result_path = Path(__file__).with_name("grammar-summary.json")
    result_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "baseline_callsites"}, ensure_ascii=False, indent=2))
    assert not mismatches


if __name__ == "__main__":
    main()
