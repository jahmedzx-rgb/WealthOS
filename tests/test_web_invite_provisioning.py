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


def test_requires_one_admin_and_two_unique_member_invites(monkeypatch):
    monkeypatch.setenv("WEB_ADMIN_INVITE_CODE", "same-code-123456")
    monkeypatch.setenv("WEB_INVITE_CODES", "same-code-123456,member-code-123456")
    with pytest.raises(RuntimeError): _invite_hashes_from_env()
    monkeypatch.setenv("WEB_ADMIN_INVITE_CODE", "secure-admin-code-0001")
    monkeypatch.setenv("WEB_INVITE_CODES", "secure-member-code-0001")
    with pytest.raises(RuntimeError): _invite_hashes_from_env()


def test_provisions_hashes_only_and_is_idempotent(monkeypatch):
    codes = ["secure-admin-code-0001", "secure-member-code-0001", "secure-member-code-0002"]
    monkeypatch.setenv("WEB_ADMIN_INVITE_CODE", codes[0])
    monkeypatch.setenv("WEB_INVITE_CODES", ",".join(codes[1:]))
    empty = Connection()
    _provision_invites(empty)
    assert len(empty.value.inserted) == 3
    assert empty.value.inserted[0][0] == hashlib.sha256(codes[0].encode()).hexdigest()
    assert empty.value.inserted[0][1] is True
    assert all(not row[1] for row in empty.value.inserted[1:])
    assert all(code not in repr(empty.value.inserted) for code in codes)
    populated = Connection(count=3)
    _provision_invites(populated)
    assert populated.value.inserted == []
