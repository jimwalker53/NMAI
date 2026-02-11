from __future__ import annotations

from nmia import seed
from nmia.auth.models import User
from nmia.core.models import ConnectorInstance, Enclave, Finding, Identity, Job


def test_seed_is_idempotent_when_run_multiple_times(db_session, monkeypatch):
    db_session.add(
        User(
            username="seed-admin",
            password_hash="SAMPLE-TEST-HASH",
            email="seed-admin@example.local",
        )
    )
    db_session.flush()

    monkeypatch.setattr(seed, "SessionLocal", lambda: db_session)

    answers = iter(["y", "y", "y", "y", "y", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    seed.main()
    first_counts = {
        "enclaves": db_session.query(Enclave).filter(Enclave.name == "SAMPLE Lab Enclave").count(),
        "connectors": db_session.query(ConnectorInstance).filter(ConnectorInstance.name.like("%SAMPLE%")).count(),
        "jobs": db_session.query(Job).filter(Job.error_message == "SAMPLE seed job").count(),
        "identities": db_session.query(Identity).filter(Identity.display_name.like("%SAMPLE%")).count(),
        "findings": sum(1 for f in db_session.query(Finding).all() if f.raw_data.get("sample") is True),
    }

    seed.main()
    second_counts = {
        "enclaves": db_session.query(Enclave).filter(Enclave.name == "SAMPLE Lab Enclave").count(),
        "connectors": db_session.query(ConnectorInstance).filter(ConnectorInstance.name.like("%SAMPLE%")).count(),
        "jobs": db_session.query(Job).filter(Job.error_message == "SAMPLE seed job").count(),
        "identities": db_session.query(Identity).filter(Identity.display_name.like("%SAMPLE%")).count(),
        "findings": sum(1 for f in db_session.query(Finding).all() if f.raw_data.get("sample") is True),
    }

    assert first_counts == {
        "enclaves": 1,
        "connectors": 2,
        "jobs": 2,
        "identities": 4,
        "findings": 4,
    }
    assert second_counts == first_counts
