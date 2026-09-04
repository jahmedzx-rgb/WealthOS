import hashlib
import pytest
from deploy.run_migrations import _invite_hashes_from_env, _provision_invites


class Cursor:
    def __init__(self, count=0): self.count, self.inserted = count, []
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def execute(self, _sql, _params=None): return None
    def fetchone(self): return (self.count,)
    def executemany(self, _sql, rows): self.inserted.extend(rows)


class Connection:
    def __init__(self, count=0): self.value = Cursor(count)
    def cursor(self): return self.value


def test_requires_exactly_ten_unique_invites(monkeypatch):
    monkeypatch.setenv("WEB_INVITE_CODES", ",".join(["same-code-123456"] * 10))
    with pytest.raises(RuntimeError): _invite_hashes_from_env()
    monkeypatch.setenv("WEB_INVITE_CODES", ",".join(f"secure-invite-{number:04d}" for number in range(9)))
    with pytest.raises(RuntimeError): _invite_hashes_from_env()


def test_provisions_hashes_only_and_is_idempotent(monkeypatch):
    codes = [f"secure-invite-{number:04d}" for number in range(10)]
    monkeypatch.setenv("WEB_INVITE_CODES", ",".join(codes))
    empty = Connection()
    _provision_invites(empty)
    assert len(empty.value.inserted) == 10
    assert empty.value.inserted[0][0] == hashlib.sha256(codes[0].encode()).hexdigest()
    assert all(code not in repr(empty.value.inserted) for code in codes)
    populated = Connection(count=10)
    _provision_invites(populated)
    assert populated.value.inserted == []
