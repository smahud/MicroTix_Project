#!/usr/bin/env python3
"""Check the active docs only. This does not test or approve the application."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import ipaddress
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit


REQUIRED = {
    'README.md', 'docs/README.md', 'docs/PRODUCT.md', 'docs/ARCHITECTURE.md',
    'docs/RADIUS.md', 'docs/ROUTEROS.md', 'docs/FINANCE.md', 'docs/ACS.md',
    'docs/I18N.md', 'docs/UI_UX.md', 'docs/OPERATIONS.md', 'docs/ACCEPTANCE.md',
    'docs/IMPLEMENTATION_PLAN.md', 'docs/MASTER_PROMPT.md', 'docs/AUDIT_REPORT.md',
    'docs/tasks.json', 'docs/test-cases.json', 'docs/defaults.json',
    'docs/branding.json', 'docs/tools/check_docs.py',
}
MANIFEST = 'docs/repository-manifest.json'
DYNAMIC_DIRS = ('docs/evidence/', 'docs/runbooks/', 'docs/adr/')
DYNAMIC_FILES = {'docs/progress.md', 'docs/compatibility.md'}
LINK = re.compile(r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)(?:\s+"[^"]*")?\)')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(root: Path, name: str):
    return json.loads((root / name).read_text(), object_pairs_hook=unique_pairs)


def static_files(root: Path) -> list[str]:
    files = ['README.md']
    for path in sorted((root / 'docs').rglob('*')):
        name = path.relative_to(root).as_posix()
        require(not path.is_symlink(), f'symlink in docs: {name}')
        if not path.is_file() or name == MANIFEST:
            continue
        if name in DYNAMIC_FILES or name.startswith(DYNAMIC_DIRS):
            continue
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        files.append(name)
    require(REQUIRED <= set(files), f'missing docs: {sorted(REQUIRED - set(files))}')
    return sorted(files)


def inventory(root: Path, paths: list[str]) -> list[dict]:
    records = []
    for name in paths:
        path = root / name
        require(path.is_file() and not path.is_symlink(), f'not a regular file: {name}')
        raw = path.read_bytes()
        records.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    return records


def check_links(root: Path, paths: list[str]) -> int:
    count = 0
    for name in paths:
        if not name.endswith('.md'):
            continue
        path = root / name
        text = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
        for match in LINK.finditer(text):
            target = unquote(match.group(1).strip('<>'))
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            dest = (path.parent / parts.path).resolve()
            require(dest.is_relative_to(root), f'link outside repo in {name}: {target}')
            # The manifest is created by --refresh and read/validated below.
            require(dest.is_file() or dest == root / MANIFEST, f'broken link in {name}: {target}')
            count += 1
    return count


def check_tasks(root: Path) -> tuple[int, int]:
    doc = read_json(root, 'docs/tasks.json')
    tasks = doc['tasks']
    ids = [t['id'] for t in tasks]
    require(len(ids) == len(set(ids)) == 85, 'expected 85 unique task IDs')
    allowed = {'R1', 'R2', 'R3', 'R4', 'SCOPED_R1_R4'}
    graph = {t['id']: t['depends_on'] for t in tasks}
    order = doc['topological_order']
    require(len(order) == len(ids) and set(order) == set(ids), 'topological order task set mismatch')
    positions = {name: i for i, name in enumerate(order)}
    edges = 0
    for t in tasks:
        require(t['release'] in allowed, f'invalid task release: {t["id"]}')
        require(t['goal'] and len(t['done_when']) >= 2, f'incomplete task: {t["id"]}')
        seen = set()
        for dep in t['depends_on']:
            require(dep['id'] in graph, f'unknown dependency in {t["id"]}: {dep["id"]}')
            require(dep['milestone'] in {'contract', 'build', 'verified'}, 'invalid dependency milestone')
            key = (dep['id'], dep['milestone'])
            require(key not in seen, f'duplicate dependency: {t["id"]}')
            require(positions[dep['id']] < positions[t['id']], f'cycle/order violation: {t["id"]}')
            seen.add(key)
            edges += 1
    return len(tasks), edges


def check_cases(root: Path) -> tuple[int, int, int]:
    doc = read_json(root, 'docs/test-cases.json')
    require(doc['kind'] == 'test_design_not_execution_evidence', 'test catalog must remain design')
    require(doc['initial_status'] == 'NOT_RUN', 'catalog cannot claim executed results')
    ids, assertion_ids, requirements = set(), set(), set()
    owned = '\n'.join((root / name).read_text() for name in REQUIRED if name.endswith('.md') and 'AUDIT_REPORT' not in name)
    for case in doc['cases']:
        require(case['id'] not in ids, f'duplicate case: {case["id"]}')
        ids.add(case['id'])
        require(case['release'] in {'R1', 'R2', 'R3', 'R4'}, f'invalid case release: {case["id"]}')
        require(case['actions'] and case['assertions'], f'incomplete case: {case["id"]}')
        require('actual' not in case and 'result' not in case, 'execution evidence mixed into design')
        for req in case['requirement_ids']:
            require(re.search(r'(?<![A-Z0-9])' + re.escape(req) + r'(?![0-9])', owned), f'unresolved requirement: {req}')
            requirements.add(req)
        for assertion in case['assertions']:
            require(assertion['id'] not in assertion_ids, f'duplicate assertion: {assertion["id"]}')
            require(assertion['expected'] and 'actual' not in assertion, 'invalid expected assertion')
            assertion_ids.add(assertion['id'])
    require(len(ids) == 256 and len(assertion_ids) == 662, 'baseline scenario/assertion set incomplete')
    require('SEC-DEC-01' not in json.dumps(doc), 'obsolete MFA blocker in active tests')
    return len(ids), len(assertion_ids), len(requirements)


def check_defaults(root: Path) -> int:
    doc = read_json(root, 'docs/defaults.json')
    values, aliases = {}, set()
    for p in doc['parameters']:
        key = p['key']
        require(key not in values, f'duplicate parameter: {key}')
        value = p['default']
        kind = p['type']
        ok = {
            'integer': type(value) is int,
            'boolean': type(value) is bool,
            'string': isinstance(value, str),
            'decimal_string': isinstance(value, str),
            'array': isinstance(value, list),
            'cidr': isinstance(value, str),
        }.get(kind, False)
        require(value is None and p['nullable'] or ok, f'default type mismatch: {key}')
        if value is not None and kind == 'decimal_string':
            require(Decimal(value).is_finite(), f'non-finite decimal: {key}')
        if value is not None and kind == 'cidr':
            ipaddress.ip_network(value, strict=True)
        bounds = p['bounds']
        if value is not None and kind in {'integer', 'decimal_string'}:
            number = Decimal(str(value))
            if 'minimum' in bounds:
                require(number >= Decimal(str(bounds['minimum'])), f'default below minimum: {key}')
            if 'maximum' in bounds:
                require(number <= Decimal(str(bounds['maximum'])), f'default above maximum: {key}')
        require(p['unit'] and p['scope'] and p['change_rule'], f'missing parameter metadata: {key}')
        for alias in p.get('legacy_aliases', []):
            require(alias not in aliases, f'duplicate alias: {alias}')
            aliases.add(alias)
        values[key] = value
    require(not (aliases & values.keys()), 'alias collides with canonical parameter')
    require(values['router.connect_timeout_s'] <= values['router.read_timeout_s'] <= values['router.job_deadline_s'], 'invalid timeouts')
    require(values['job.heartbeat_s'] * 2 < values['job.lease_s'], 'invalid heartbeat/lease')
    require(Decimal(values['backup.warn_ratio']) < Decimal(values['backup.stop_ratio']), 'invalid disk watermarks')
    require(values['ledger.retention_years'] >= 10, 'financial retention below minimum')
    brand = read_json(root, 'docs/branding.json')
    require(brand['project_id'] == 'microtix', 'stable project ID changed')
    require(all(brand[k] for k in ('project_name', 'application_name', 'display_name')), 'missing display defaults')
    require(brand['environment_overrides']['display_name'] == 'BRAND_NAME', 'brand resolver mapping changed')
    return len(values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--refresh', action='store_true', help='explicitly update the active docs inventory after reviewed edits')
    args = parser.parse_args()
    root = args.root.resolve()
    paths = static_files(root)
    links = check_links(root, paths)
    task_count, edge_count = check_tasks(root)
    case_count, assertion_count, req_count = check_cases(root)
    param_count = check_defaults(root)
    for name in paths:
        if name.endswith('.json'):
            read_json(root, name)
    actual = inventory(root, paths)
    if args.refresh:
        payload = {'revision': '2.2', 'scope': 'README and active documentation; not application runtime',
                   'source_commit': '19b954308a7573bc449f551400d053fba1c089d7',
                   'excluded': [MANIFEST, *sorted(DYNAMIC_FILES), *DYNAMIC_DIRS, '**/__pycache__/**', '**/*.pyc'],
                   'files': actual}
        (root / MANIFEST).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    manifest = read_json(root, MANIFEST)
    for record in manifest['files']:
        name = record['path']
        require(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts, 'unsafe manifest path')
    require(manifest['files'] == actual, 'manifest mismatch; review changed docs, then run --refresh explicitly')
    print(json.dumps({'result': 'PASS', 'scope': 'documentation_static_only', 'files': len(paths) + 1,
                      'internal_links': links, 'tasks': task_count, 'dependency_edges': edge_count,
                      'designed_cases': case_count, 'designed_assertions': assertion_count,
                      'referenced_requirement_ids': req_count, 'technical_defaults': param_count,
                      'application_runtime_tests_executed': 0, 'production_readiness': 'NOT_EVALUATED'}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'result': 'FAIL', 'scope': 'documentation_static_only', 'error': str(exc)}), file=sys.stderr)
        sys.exit(1)
