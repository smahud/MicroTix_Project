"""State machine job — transisi sah/ditolak sesuai ARCHITECTURE.md §6."""
from __future__ import annotations

import pytest

from domains.jobs.models import JobState, VALID_TRANSITIONS, CANCEL_OK_STATES


def test_queued_can_claim_or_cancel():
    assert JobState.CLAIMED in VALID_TRANSITIONS[JobState.QUEUED]
    assert JobState.CANCELLED in VALID_TRANSITIONS[JobState.QUEUED]
    assert JobState.EXECUTING not in VALID_TRANSITIONS[JobState.QUEUED]


def test_executing_cannot_jump_to_succeeded():
    assert JobState.SUCCEEDED not in VALID_TRANSITIONS[JobState.EXECUTING]
    assert JobState.VERIFYING in VALID_TRANSITIONS[JobState.EXECUTING]
    assert JobState.UNCERTAIN in VALID_TRANSITIONS[JobState.EXECUTING]
    assert JobState.RECOVERY_REQUIRED in VALID_TRANSITIONS[JobState.EXECUTING]


def test_uncertain_requires_readback_before_retry():
    # uncertain → retry_wait hanya bila terbukti belum diterapkan (engine),
    # tapi transisi ke verifying (readback) selalu sah.
    assert JobState.VERIFYING in VALID_TRANSITIONS[JobState.UNCERTAIN]
    assert JobState.RETRY_WAIT in VALID_TRANSITIONS[JobState.UNCERTAIN]


def test_terminal_states_have_no_outgoing():
    for state in (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED):
        assert len(VALID_TRANSITIONS[state]) == 0


def test_cancel_allowed_states():
    assert JobState.QUEUED in CANCEL_OK_STATES
    assert JobState.EXECUTING not in CANCEL_OK_STATES
