#!/usr/bin/env python3
"""Pengukuran kontras WCAG 2.2 AA untuk pasangan warna token MicroTix.

UI_UX.md §2: teks normal 4,5:1; teks besar dan kontrol bermakna 3:1 — diukur.
Sumber token: src/styles/tokens.css.
"""
import re
import sys
from pathlib import Path

TOKENS_FILE = Path(__file__).resolve().parents[1] / 'src' / 'styles' / 'tokens.css'

def srgb_to_lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def luminance(hexcolor: str) -> float:
    h = hexcolor.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)

def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

# (fg, bg, label, ambang)
CHECKS = [
    ('--mt-text', '#F4F6F8', 'Teks utama pada latar halaman', 4.5),
    ('--mt-text', '#FFFFFF', 'Teks utama pada kartu', 4.5),
    ('--mt-text-secondary', '#FFFFFF', 'Teks sekunder pada kartu', 4.5),
    ('--mt-text-secondary', '#F4F6F8', 'Teks sekunder pada latar halaman', 4.5),
    ('--mt-primary', '#FFFFFF', 'Tautan/aksi primer pada kartu', 4.5),
    ('#FFFFFF', '--mt-primary', 'Teks tombol primer', 4.5),
    ('#FFFFFF', '--mt-header-admin', 'Teks putih pada header admin navy', 4.5),
    ('--mt-success-fg', '--mt-success-bg', 'Badge sukses', 4.5),
    ('--mt-warning-fg', '--mt-warning-bg', 'Badge peringatan', 4.5),
    ('--mt-danger-fg', '--mt-danger-bg', 'Badge gagal', 4.5),
    ('--mt-info-fg', '--mt-info-bg', 'Badge proses', 4.5),
    ('--mt-neutral-fg', '--mt-neutral-bg', 'Badge netral', 4.5),
    ('--mt-warning-fg', '#FEF3C7', 'Banner dev-mode (pengembangan)', 4.5),
]

def main() -> int:
    css = TOKENS_FILE.read_text()
    tokens = dict(re.findall(r'(--mt-[a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})', css))
    failures = 0
    print(f'{"pasangan":48} {"rasio":>7}  {"batas":>5}  hasil')
    for fg, bg, label, threshold in CHECKS:
        fg_v = tokens.get(fg, fg)
        bg_v = tokens.get(bg, bg)
        ratio = contrast(fg_v, bg_v)
        ok = ratio >= threshold
        if not ok:
            failures += 1
        print(f'{label:48} {ratio:6.2f}:1 {threshold:5}  {"PASS" if ok else "FAIL"}')
    print(f'\n{len(CHECKS) - failures}/{len(CHECKS)} PASS')
    return 1 if failures else 0

if __name__ == '__main__':
    sys.exit(main())
