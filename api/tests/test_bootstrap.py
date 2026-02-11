from nmia import bootstrap


class _FakeUsersQuery:
    def count(self) -> int:
        return 1


class _FakeDB:
    def __init__(self) -> None:
        self.closed = False

    def query(self, model):
        return _FakeUsersQuery()

    def close(self) -> None:
        self.closed = True

    def rollback(self) -> None:
        raise AssertionError("rollback should not be called when bootstrap is skipped")


def test_bootstrap_refuses_when_users_exist(monkeypatch, capsys):
    fake_db = _FakeDB()

    monkeypatch.setattr(bootstrap, "SessionLocal", lambda: fake_db)

    bootstrap.main()

    output = capsys.readouterr().out
    assert "Bootstrap not required." in output
    assert fake_db.closed is True
