/**
 * Pemetaan kode status domain → tone visual + kunci label katalog.
 * UI_UX.md §2: warna bukan satu-satunya penanda — selalu dengan teks (+ikon pada badge).
 * "Offline" memakai netral/kuning, bukan merah.
 */
export type Tone = 'success' | 'warning' | 'danger' | 'neutral' | 'info';

/* ---------- Job state (ARCHITECTURE.md §6) ---------- */
export function jobStateTone(state: string): Tone {
  switch (state) {
    case 'succeeded':
    case 'verified':
      return 'success';
    case 'failed':
      return 'danger';
    case 'uncertain':
    case 'recovery_required':
      return 'warning';
    case 'cancelled':
      return 'neutral';
    default:
      return 'info';
  }
}

/* ---------- Dimensi koneksi (bukan pembayaran, bukan enabled) ---------- */
export function connectionTone(v: 'online' | 'offline' | 'unknown'): Tone {
  switch (v) {
    case 'online':
      return 'success';
    case 'offline':
      return 'warning'; // netral/kuning — bukan merah (UI_UX.md §2)
    default:
      return 'neutral';
  }
}

export function isolationTone(v: string): Tone {
  switch (v) {
    case 'normal':
      return 'success';
    case 'isolated':
      return 'warning';
    case 'awaiting_verification':
      return 'warning';
    case 'hold':
      return 'neutral';
    default:
      return 'neutral';
  }
}

export function paymentTone(v: string): Tone {
  switch (v) {
    case 'paid':
      return 'success';
    case 'partial':
    case 'unbilled':
      return 'warning';
    default: // not_billed
      return 'neutral';
  }
}

export function jobDimensionTone(v: string): Tone {
  switch (v) {
    case 'none':
      return 'neutral';
    case 'queued':
    case 'running':
      return 'info';
    case 'needs_review':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function lifecycleTone(v: string): Tone {
  switch (v) {
    case 'provisioned':
      return 'success';
    case 'pending':
    case 'provisioning':
      return 'info';
    case 'conflict':
    case 'failed':
      return 'danger';
    default: // draft/terminated/archived
      return 'neutral';
  }
}

export function enforcementTone(v: string): Tone {
  switch (v) {
    case 'radius_authoritative':
      return 'success';
    case 'radius_shadow':
      return 'warning';
    case 'degraded':
      return 'danger';
    default: // local
      return 'neutral';
  }
}

export function monitorGroupTone(g: string): Tone {
  switch (g) {
    case 'healthy':
      return 'success';
    case 'disturbed':
      return 'warning';
    case 'management_unreachable':
      return 'warning';
    case 'stale_data':
      return 'warning';
    default: // unmonitored
      return 'neutral';
  }
}

export function accountStateTone(v: string): Tone {
  switch (v) {
    case 'active':
      return 'success';
    case 'suspended':
      return 'warning';
    case 'expired':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function submissionStateTone(v: string): Tone {
  switch (v) {
    case 'approved':
      return 'success';
    case 'rejected':
      return 'danger';
    case 'revision_requested':
      return 'warning';
    case 'reviewing':
      return 'info';
    default: // submitted
      return 'neutral';
  }
}

export function subscriptionStateTone(v: string): Tone {
  switch (v) {
    case 'active':
    case 'free':
      return 'success';
    case 'grace':
      return 'warning';
    case 'restricted':
      return 'warning';
    case 'ended':
      return 'neutral';
    default:
      return 'info';
  }
}

/* ---------- Freshness (UI_UX.md: stale/unknown bukan nol) ---------- */
export type Freshness = 'fresh' | 'stale' | 'unknown';

export function freshness(observedAt: string | null, staleMinutes = 15): Freshness {
  if (!observedAt) return 'unknown';
  const ageMin = (Date.now() - new Date(observedAt).getTime()) / 60_000;
  if (ageMin > staleMinutes) return 'stale';
  return 'fresh';
}

export function freshnessTone(f: Freshness): Tone {
  switch (f) {
    case 'fresh':
      return 'success';
    case 'stale':
      return 'warning';
    default:
      return 'neutral';
  }
}

/* ---------- Billing internet M6 (U09 — TK-604) ---------- */

export function invoiceStateTone(v: string): Tone {
  switch (v) {
    case 'paid':
      return 'success';
    case 'partial':
      return 'warning';
    case 'open':
      return 'info';
    case 'void':
      return 'neutral';
    default: // draft
      return 'neutral';
  }
}

export function paymentStateTone(v: string): Tone {
  switch (v) {
    case 'verified':
      return 'success';
    case 'submitted':
      return 'info';
    case 'rejected':
      return 'danger';
    default:
      return 'neutral';
  }
}

export function agingBucketTone(v: string): Tone {
  switch (v) {
    case 'not_due':
      return 'neutral';
    case 'current':
      return 'info';
    case 'd31_60':
      return 'warning';
    default: // d61_90, d90_plus
      return 'danger';
  }
}
