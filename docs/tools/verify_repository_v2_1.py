#!/usr/bin/env python3
"""Read-only MicroTix documentation verifier. Never installs or runs payloads."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

MANIFEST = "sumber/source-manifest_v2_1.md"
ZIP_ROOT = "MicroTix-Documentation-v2_1-Final"
REVISION = "2.1-build.1"
FILE_COUNT = 57
MAX_TOTAL_BYTES = 50 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(value):
    require(isinstance(value, str) and bool(value), "empty path")
    require(not any(c in value for c in "\\\x00\r\n\t|:"), "unsafe path characters")
    path = PurePosixPath(value)
    require(not path.is_absolute(), "absolute path")
    require(all(x not in ("", ".", "..") for x in value.split("/")), "path traversal or noncanonical path")
    require(path.as_posix() == value, "noncanonical path")
    require(all(not x.startswith(".") for x in path.parts), "hidden file/directory is not packaged")
    return value


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_tree(root):
    require(not root.is_symlink() and root.is_dir(), "root must be a nonsymlink directory")
    result = {}
    total = 0
    for item in sorted(root.rglob("*")):
        require(not item.is_symlink(), "symlink: " + str(item))
        if item.is_dir():
            safe_path(item.relative_to(root).as_posix())
            continue
        require(item.is_file(), "nonregular file")
        rel = safe_path(item.relative_to(root).as_posix())
        total += item.stat().st_size
        require(total <= MAX_TOTAL_BYTES, "package exceeds documentation size limit")
        result[rel] = item.read_bytes()
    return result


def read_zip(path):
    result = {}
    total = 0
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) == FILE_COUNT, "unexpected ZIP entry count")
        seen = set()
        for info in entries:
            name = safe_path(info.filename)
            require(name not in seen, "duplicate ZIP entry")
            seen.add(name)
            require(name.startswith(ZIP_ROOT + "/"), "unexpected ZIP root")
            rel = safe_path(name[len(ZIP_ROOT) + 1:])
            require(not info.is_dir(), "directory entry not permitted")
            kind = stat.S_IFMT(info.external_attr >> 16)
            require(kind in (0, stat.S_IFREG), "ZIP symlink/nonregular entry")
            require(not info.flag_bits & 1, "encrypted ZIP entry not permitted")
            total += info.file_size
            require(total <= MAX_TOTAL_BYTES, "ZIP expands beyond documentation limit")
            data = archive.read(info)
            require(len(data) == info.file_size, "ZIP size mismatch")
            result[rel] = data
        require(archive.testzip() is None, "ZIP CRC failure")
    return result


def parse_manifest(data):
    value = data.decode("utf-8", errors="strict")
    meta_blocks = re.findall(
        r"<!-- MANIFEST_META_BEGIN -->\n```json\n(.*?)\n```\n<!-- MANIFEST_META_END -->",
        value, flags=re.S,
    )
    require(len(meta_blocks) == 1, "expected one metadata block")
    meta = json.loads(meta_blocks[0], object_pairs_hook=unique_pairs)
    require(meta.get("schema_version") == "2.1", "manifest schema mismatch")
    require(meta.get("package_revision") == REVISION, "package revision mismatch")
    require(meta.get("manifest_self_path") == MANIFEST, "self path mismatch")
    require(meta.get("package_file_count") == FILE_COUNT, "unexpected package count")
    require(meta.get("payload_entries") == FILE_COUNT - 1, "unexpected manifest count")
    row_blocks = re.findall(r"<!-- MANIFEST_ROWS_BEGIN -->\n(.*?)\n<!-- MANIFEST_ROWS_END -->", value, flags=re.S)
    require(len(row_blocks) == 1, "expected one manifest table")
    lines = row_blocks[0].splitlines()
    require(lines[:2] == ["| Path sumber | Target repository | Kelas | Ukuran byte | SHA-256 |", "|---|---|---|---:|---|"], "manifest table header mismatch")
    rows = []
    paths = set()
    destinations = {"docs/source/source-manifest_v2_1.md".casefold()}
    for line in lines[2:]:
        match = re.fullmatch(r"\| ([^|]+) \| ([^|]+) \| ([A-Z_]+) \| (0|[1-9][0-9]*) \| ([a-f0-9]{64}) \|", line)
        require(match is not None, "malformed manifest row")
        path, target, classification, size, digest = match.groups()
        safe_path(path)
        safe_path(target)
        require(path != MANIFEST, "self hash prohibited")
        require(path.casefold() not in paths, "duplicate/casefold source")
        require(target.casefold() not in destinations, "duplicate/casefold target")
        paths.add(path.casefold())
        destinations.add(target.casefold())
        require(classification in ("ACTIVE", "PROVENANCE", "AUDIT_ONLY", "VERIFICATION_TOOL"), "invalid file class")
        rows.append((path, int(size), digest))
    require(len(rows) == FILE_COUNT - 1 and rows, "manifest missing rows")
    require([r[0] for r in rows] == sorted((r[0] for r in rows), key=lambda p: p.encode("utf-8")), "unsorted manifest")
    return meta, rows


def verify(files):
    require(len(files) == FILE_COUNT, "file set size mismatch")
    require(len({p.casefold() for p in files}) == len(files), "casefold filename collision")
    for path in files:
        safe_path(path)
        require(not path.casefold().endswith(".zip"), "nested ZIP not permitted")
    require(MANIFEST in files, "active manifest missing")
    meta, rows = parse_manifest(files[MANIFEST])
    expected = {p for p, _, _ in rows} | {MANIFEST}
    require(set(files) == expected, "missing or extra unlisted payload file")
    for path, size, digest in rows:
        require(len(files[path]) == size, "size mismatch: " + path)
        require(sha256(files[path]) == digest, "SHA-256 mismatch: " + path)
    serialized = "".join(f"{digest}\t{size}\t{path}\n" for path, size, digest in rows).encode("utf-8")
    require(sha256(serialized) == meta.get("payload_root_sha256"), "payload root mismatch")
    require(sum(size for _, size, _ in rows) == meta.get("payload_bytes"), "payload byte total mismatch")
    return {
        "result": "PASS",
        "scope": "documentation_byte_integrity_only",
        "package_revision": REVISION,
        "package_file_count": len(files),
        "manifest_entries_verified": len(rows),
        "package_uncompressed_bytes": sum(len(v) for v in files.values()),
        "payload_bytes": meta["payload_bytes"],
        "payload_root_sha256": meta["payload_root_sha256"],
        "manifest_bytes": len(files[MANIFEST]),
        "manifest_sha256": sha256(files[MANIFEST]),
        "runtime_tests_executed": 0,
        "publisher_authenticity_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--root", type=Path, help="unmodified extracted package root")
    group.add_argument("--zip", type=Path, help="final documentation ZIP; read without extraction")
    args = parser.parse_args()
    try:
        result = verify(read_zip(args.zip) if args.zip else read_tree(args.root))
        if args.zip:
            result.update(zip_size_bytes=args.zip.stat().st_size, zip_sha256=sha256(args.zip.read_bytes()))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile, RuntimeError) as error:
        print(json.dumps({"result": "FAIL", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
