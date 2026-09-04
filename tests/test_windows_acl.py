import os
import subprocess

import pytest

from scripts.windows_acl import secure_and_verify_directory, verify_directory_acl


@pytest.mark.skipif(os.name != "nt", reason="Windows DACL contract")
def test_acl_is_enforced_and_verified_on_real_directory(tmp_path):
    target = tmp_path / "managed"
    target.mkdir()
    secure_and_verify_directory(target)
    verify_directory_acl(target)


@pytest.mark.skipif(os.name != "nt", reason="Windows DACL contract")
def test_acl_verification_rejects_broad_users_grant(tmp_path):
    target = tmp_path / "managed"
    target.mkdir()
    secure_and_verify_directory(target)
    subprocess.run(
        ["icacls.exe", str(target), "/grant", "*S-1-5-32-545:(OI)(CI)R"],
        check=True,
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    with pytest.raises(RuntimeError, match="permissions failed verification"):
        verify_directory_acl(target)
