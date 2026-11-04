import type { Locale } from '../i18n';

/**
 * I18N.md §4 — format regional.
 * Uang disimpan string numeric(20,2); pemformatan hanya di lapisan tampilan.
 */

export function formatMoney(amount: string | number, locale: Locale): string {
  const n = typeof amount === 'string' ? Number(amount) : amount;
  if (!Number.isFinite(n)) return locale === 'id' ? 'Rp—' : 'IDR —';
  if (locale === 'id') {
    const s = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(n);
    return `Rp${s}`;
  }
  return `IDR ${new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)}`;
}

export function formatDateFull(iso: string, locale: Locale): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(d);
}

export function formatDateShort(iso: string, locale: Locale): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(d);
}

export function formatDateTime(iso: string, locale: Locale): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

export function formatTimeOnly(iso: string, locale: Locale): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

/** "Data terakhir diperbarui 12 menit lalu" — relative time. */
export function formatRelative(iso: string, locale: Locale): string {
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const rtf = new Intl.RelativeTimeFormat(locale === 'id' ? 'id' : 'en', { numeric: 'auto' });
  const min = Math.round(diffMs / 60_000);
  if (min < 1) return locale === 'id' ? 'baru saja' : 'just now';
  if (min < 60) return rtf.format(-min, 'minute');
  const h = Math.round(min / 60);
  if (h < 24) return rtf.format(-h, 'hour');
  const days = Math.round(h / 24);
  return rtf.format(-days, 'day');
}

/** Zona waktu WIB/WITA/WIT dengan label (I18N.md §4). */
export function zoneLabel(tz: string): string {
  switch (tz) {
    case 'Asia/Jakarta':
      return 'WIB';
    case 'Asia/Makassar':
      return 'WITA';
    case 'Asia/Jayapura':
      return 'WIT';
    default:
      return tz;
  }
}

export function formatBytes(bytes: number, locale: Locale): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = locale === 'id' ? ['KiB', 'MiB', 'GiB', 'TiB'] : ['KiB', 'MiB', 'GiB', 'TiB'];
  let v = bytes / 1024;
  let u = 0;
  while (v >= 1024 && u < units.length - 1) {
    v /= 1024;
    u++;
  }
  const s = new Intl.NumberFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    maximumFractionDigits: 1,
  }).format(v);
  return `${s} ${units[u]}`;
}

/** Bandwidth bit/detik integer (ARCHITECTURE.md §4). */
export function formatBitsPerSecond(bps: number | null, locale: Locale): string {
  if (bps === null) return locale === 'id' ? 'tidak diketahui' : 'unknown';
  if (bps < 1000) return `${bps} bit/s`;
  const units = ['kbit/s', 'Mbit/s', 'Gbit/s'];
  let v = bps / 1000;
  let u = 0;
  while (v >= 1000 && u < units.length - 1) {
    v /= 1000;
    u++;
  }
  const s = new Intl.NumberFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    maximumFractionDigits: 1,
  }).format(v);
  return `${s} ${units[u]}`;
}

export function formatPercent(ratio: number | null, locale: Locale): string {
  if (ratio === null) return locale === 'id' ? 'tidak diketahui' : 'unknown';
  const s = new Intl.NumberFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(ratio);
  return s;
}

/** Durasi detik → "2 hari 4 jam" dsb. */
export function formatDuration(seconds: number, locale: Locale): string {
  const id = locale === 'id';
  if (seconds < 60) return id ? `${seconds} detik` : `${seconds} seconds`;
  const min = Math.floor(seconds / 60);
  if (min < 60) return id ? `${min} menit` : `${min} minutes`;
  const h = Math.floor(min / 60);
  const rem = min % 60;
  if (h < 24) return rem ? (id ? `${h} jam ${rem} menit` : `${h} h ${rem} min`) : id ? `${h} jam` : `${h} hours`;
  const d = Math.floor(h / 24);
  const remH = h % 24;
  return remH ? (id ? `${d} hari ${remH} jam` : `${d} d ${remH} h`) : id ? `${d} hari` : `${d} days`;
}

export function formatNumber(n: number, locale: Locale): string {
  return new Intl.NumberFormat(locale === 'id' ? 'id-ID' : 'en-US').format(n);
}

/** Persentase kekuatan password 0–100 sederhana untuk indikator U02. */
export function passwordStrength(pw: string): number {
  if (!pw) return 0;
  let score = Math.min(40, pw.length * 3);
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score += 15;
  if (/\d/.test(pw)) score += 15;
  if (/[^a-zA-Z0-9]/.test(pw)) score += 20;
  if (pw.length >= 16) score += 10;
  return Math.max(0, Math.min(100, score));
}
