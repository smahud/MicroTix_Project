"""Standalone grammar probe — mirrors controller parser-matrix methodology.

Extracts _canonical_uuid/_split_legacy_scope from the migration source via
AST (no Django import), then checks the full spelling matrix in both
positions plus opaque/unresolvable/ambiguity-injection cases.
"""
import ast
import sys
import uuid
from pathlib import Path

SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else
              "domains/jobs/migrations/0004_idempotency_identity.py").resolve()

tree = ast.parse(SOURCE.read_text())
wanted = {"_canonical_uuid", "_split_legacy_scope", "AmbiguousLegacyScope"}
body = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        body.append(node)
    elif isinstance(node, ast.Assign):
        targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if targets & {"_OPAQUE_RESOURCE_OPERATIONS", "_PLATFORM_OPERATIONS",
                      "_UNPARSED_OPERATION", "_PLATFORM_LITERAL"}:
            body.append(node)
    elif isinstance(node, ast.ClassDef) and node.name == "AmbiguousLegacyScope":
        body.append(node)

ns = {"_uuid": uuid, "RuntimeError": RuntimeError}
exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), "exec"), ns)

V = "abcdef12-2345-6789-abcd-ef1234567890"
OTHER = "fedcba98-7654-3210-abcd-ef1234567890"
spellings = {
    "canonical": V, "upper": V.upper(), "compact": uuid.UUID(V).hex,
    "braced": "{" + V + "}", "urn": "urn:uuid:" + V,
    "braced_urn": "{urn:uuid:" + V + "}", "uuid_only": "uuid:" + V,
    "urn_only": "urn:" + V, "repeat_uuid": "urn:uuid:uuid:" + V,
    "repeat_urn": "urn:urn:uuid:" + V, "mixed": "uuid:urn:uuid:" + V,
    "uuid_repeat": "uuid:uuid:" + V,
}
fails = 0
for label, sp in spellings.items():
    assert str(uuid.UUID(sp)) == V, f"stdlib rejects {label}?!"
    for where in ("tenant", "resource"):
        scope = (f"payment_submission:{sp}:" if where == "tenant"
                 else f"router_backup:{OTHER}:{sp}")
        parts = ns["_split_legacy_scope"](scope)
        if where == "tenant":
            ok = parts is not None and ns["_canonical_uuid"](parts[1]) == V and parts[2] == ""
        else:
            ok = (parts is not None and ns["_canonical_uuid"](parts[1]) == OTHER
                  and ns["_canonical_uuid"](parts[2]) == V)
        if not ok:
            fails += 1
        print(f"{label:<12} {where:<8} {'OK  ' if ok else 'FAIL'} -> {parts}")

p = ns["_split_legacy_scope"](f"identity_conflict_resolve:uuid:{V}:0f1e2d3c4b5a6978")
print("opaque uuid tenant   ->", p)
assert p == ("identity_conflict_resolve", f"uuid:{V}", "0f1e2d3c4b5a6978")

print("garbage              ->", ns["_split_legacy_scope"]("payment_submission:zz:not-a-uuid:x:"))
print("no colon             ->", ns["_split_legacy_scope"]("payment_submission"))
print("upper URN (rejected) ->", ns["_split_legacy_scope"]("payment_submission:URN:UUID:" + V + ":"))

try:
    ns["_split_legacy_scope"]("op:a:b:c", tenant_valid=lambda p: True,
                              resource_valid=lambda p: True)
    print("ambiguity injection  -> NO RAISE (BAD)")
    fails += 1
except ns["AmbiguousLegacyScope"]:
    print("ambiguity injection  -> raised OK")

print("FAILS:", fails)
sys.exit(1 if fails else 0)
