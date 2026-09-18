from database.engine import get_db
from core.audit.audit_engine import get_audit_engine


def test_sqlite_wal_integrity():
    db = get_db()
    assert db.verify_integrity() is True


def test_audit_event_chain_invariants():
    audit = get_audit_engine()
    ev = audit.log_event(
        event_type="TEST_EVENT",
        component="TestUnit",
        action="RUN_ASSERT",
        status="SUCCESS",
        details={"key": "val_123"}
    )
    assert ev.sequence_num > 0
    assert len(ev.content_hash) == 64

    # Verify chain
    valid, count, err = audit.verify_audit_chain_integrity()
    assert valid is True
    assert err is None
