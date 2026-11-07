#!/usr/bin/env python3
"""Provisioner lab GNS3 MicroTix Phase-2 — API-driven, stdlib saja.

Status: IMPLEMENTED, BELUM DIVERIFIKASI terhadap controller GNS3 nyata
(aset lab belum tersedia di sesi penulisan — lihat lab/README.md). Skrip
gagal jujur (exit != 0) bila controller/asets tidak memadai; TIDAK pernah
mengklaim provisioning sukses tanpa respons API nyata.

Perilaku (docs/OPERATIONS.md):
- Family API (v2/v3) dideteksi dari endpoint /version — bukan menambah
  prefix /v2 secara buta.
- Idempoten berdasarkan nama project; node dibuat dari template controller.
- --cleanup HANYA menghapus project milik run ini (prefix microtix-) —
  tidak menyentuh project lain di shared controller.
- Tanpa mutasi router: provisioning node saja; enrollment router tetap
  melalui aplikasi MicroTix (otorisasi Owner).

Pemakaian:
  python3 lab/provision.py --controller http://127.0.0.1:3080 \
      --topology lab/topology-phase2.json --stage B --project microtix-phase2-b
  python3 lab/provision.py --controller http://127.0.0.1:3080 \
      --project microtix-phase2-b --cleanup
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

PREFIX = "microtix-"


def _req(controller: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    url = f"{controller.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode()
        return json.loads(text) if text.strip() else {}


def _api_family(controller: str) -> str:
    """Deteksi family API dari /version (OPERATIONS.md — tanpa prefix buta)."""
    ver = _req(controller, "/version")
    for key in ("version", "local_server"):
        value = ver.get(key) if isinstance(ver, dict) else None
        if isinstance(value, dict) and "version" in value:
            value = value["version"]
        if isinstance(value, str) and value.startswith(("2", "3")):
            return f"/v{value.split('.')[0]}"
    raise SystemExit("GAGAL: /version controller tidak dikenal — konfigurasi controller lab diperlukan.")


def _find_template(base: str, family: str, name: str) -> str:
    templates = _req(base, f"{family}/templates")
    for tpl in templates:
        if tpl.get("name") == name:
            return str(tpl["template_id"])
    raise SystemExit(f"GAGAL: template '{name}' tidak ada di controller — siapkan template lab (lab/README.md).")


def _project(base: str, family: str, name: str) -> dict | None:
    for proj in _req(base, f"{family}/projects"):
        if proj.get("name") == name:
            return proj
    return None


def provision(controller: str, topology_path: str, stage: str, project_name: str) -> None:
    with open(topology_path, encoding="utf-8") as fh:
        topo = json.load(fh)
    family = _api_family(controller)
    base = controller.rstrip("/")
    if not project_name.startswith(PREFIX):
        raise SystemExit(f"GAGAL: nama project harus berprefix {PREFIX} (scope cleanup aman).")

    spec = topo["stages"][stage]
    nodes, links = list(spec["nodes"]), list(spec["links"])
    if "extends" in spec:  # tahap B extends A
        parent = topo["stages"][spec["extends"]]
        nodes = list(parent["nodes"]) + nodes
        links = list(parent["links"]) + links

    proj = _project(base, family, project_name)
    if proj is None:
        proj = _req(base, f"{family}/projects", "POST", {"name": project_name})
        print(f"project dibuat: {proj['name']} ({proj['project_id']})")
    else:
        print(f"project sudah ada (idempoten): {proj['name']}")

    template_ids = {}
    for node in nodes:
        tpl_name = node["template"]
        if tpl_name not in template_ids:
            template_ids[tpl_name] = _find_template(base, family, tpl_name)
        created = _req(
            base, f"{family}/projects/{proj['project_id']}/templates/{template_ids[tpl_name]}",
            "POST", {"name": node["name"], "default_name_format": node["name"]},
        )
        print(f"node: {created.get('name')} (status={created.get('status')})")

    for link in links:
        (a_node, a_port), (b_node, b_port) = link["a"], link["b"]
        # Port node ditemukan via adapter; GNS3 v2/v3 memakai label port template.
        a = _find_port(base, family, proj["project_id"], a_node, a_port)
        b = _find_port(base, family, proj["project_id"], b_node, b_port)
        _req(base, f"{family}/projects/{proj['project_id']}/links", "POST", {"nodes": [a, b]})
        print(f"link: {a_node}:{a_port} <-> {b_node}:{b_port} ({link.get('purpose', '')})")

    _req(base, f"{family}/projects/{proj['project_id']}/nodes/start", "POST", {})
    print("semua node distart — tunggu boot CHR, lalu jalankan enrollment via UI MicroTix.")
    if "overlapping_lan" in spec:
        info = spec["overlapping_lan"]
        print(f"PERHATIAN tahap overlap: {info['subnet']} pada {info['nodes']} — {info['note']}")


def _find_port(base: str, family: str, project_id: str, node_name: str, port_label: str) -> dict:
    for node in _req(base, f"{family}/projects/{project_id}/nodes"):
        if node.get("name") == node_name:
            for port in node.get("ports", []):
                if port.get("name") == port_label or port.get("short_name") == port_label:
                    return {"adapter_number": port["adapter_number"], "port_number": port["port_number"], "node_id": node["node_id"]}
    raise SystemExit(f"GAGAL: port {node_name}:{port_label} tidak ditemukan (cek label port template).")


def cleanup(controller: str, project_name: str) -> None:
    family = _api_family(controller)
    base = controller.rstrip("/")
    proj = _project(base, family, project_name)
    if proj is None:
        print(f"project {project_name} tidak ada — tidak ada yang dihapus.")
        return
    if not project_name.startswith(PREFIX):
        raise SystemExit("GAGAL: menolak menghapus project di luar prefix lab microtix-.")
    _req(base, f"{family}/projects/{proj['project_id']}", "DELETE")
    print(f"project dihapus: {project_name} (hanya milik run ini — OPERATIONS.md).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", required=True, help="URL controller GNS3 lab (mis. http://127.0.0.1:3080)")
    parser.add_argument("--topology", help="berkas topologi JSON (lab/topology-phase2.json)")
    parser.add_argument("--stage", choices=["A", "B"], help="tahap topologi (A=1 tenant; B=+tenant overlap LAN)")
    parser.add_argument("--project", required=True, help=f"nama project (wajib prefix {PREFIX})")
    parser.add_argument("--cleanup", action="store_true", help="hapus project run ini saja")
    args = parser.parse_args()
    if args.cleanup:
        cleanup(args.controller, args.project)
        return 0
    if not args.topology or not args.stage:
        parser.error("--topology dan --stage wajib bila bukan --cleanup")
    started = time.time()
    provision(args.controller, args.topology, args.stage, args.project)
    print(f"selesai dalam {time.time() - started:.1f}s — bukti: ikuti lab/evidence-checklist.md")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as exc:
        raise SystemExit(f"GAGAL jujur: controller tidak terjangkau ({exc}) — aset lab belum siap (BLOCKED, bukan dipalsukan).") from exc
