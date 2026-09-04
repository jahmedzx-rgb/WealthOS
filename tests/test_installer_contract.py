from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (ROOT / "installer" / "WealthOSBeta.iss").read_text(encoding="utf-8")
BUILD = (ROOT / "scripts" / "build_beta.ps1").read_text(encoding="utf-8")
WIPE = (ROOT / "scripts" / "managed_wipe.py").read_text(encoding="utf-8")


def test_installer_is_single_neutral_per_user_payload_without_identity_prompt():
    assert "PrivilegesRequired=lowest" in INSTALLER
    assert "DefaultDirName={localappdata}\\Programs\\WealthOS Beta" in INSTALLER
    assert "Source: \"..\\dist\\{#AppExeName}\"" in INSTALLER
    assert "BetaIdPage" not in INSTALLER
    assert "AssignedBetaId" not in INSTALLER
    assert "allowed_beta_ids" not in BUILD
    assert "single-neutral-installer-per-windows-user" in BUILD
    assert "uuid-v4-canonical-lowercase" in BUILD
    assert "installation-uuid" in BUILD


def test_default_uninstall_preserves_data_and_explicit_removal_is_allowlisted():
    assert "RemoveDataCheck.Checked := CmdLineParamExists('/REMOVELOCALDATA=YES')" in INSTALLER
    assert "Remove WealthOS and all locally managed data" in INSTALLER
    for filename in ("wealthos.db", "wealthos.db-wal", "wealthos.db-shm"):
        assert f'"{filename}"' in WIPE
    assert "DelTree(" not in INSTALLER
    assert "IsReparsePoint(Root)" in INSTALLER
    assert "winreg.DeleteValue" in WIPE
    assert "InstallationId" in INSTALLER
    assert "IsValidInstallationId" in INSTALLER
    assert "\\instances'" in INSTALLER
    assert "DeleteManagedFlatDirectory" not in INSTALLER
    assert "DeleteRegisteredManagedFiles" not in INSTALLER
    assert "--wipe-managed-root" in INSTALLER
    assert "CurUninstallStep <> usUninstall" in INSTALLER
    assert "CurUninstallStep <> usPostUninstall" not in INSTALLER
    assert "/REMOVELOCALDATA=YES" in INSTALLER
    assert "exact_delete_resources = @('data\\wealthos.db', 'data\\wealthos.db-wal', 'data\\wealthos.db-shm')" in BUILD
    assert "recursive_delete = $false" in BUILD


def test_manifest_and_installer_are_versioned_and_hashed():
    assert "release-manifest.json" in BUILD
    assert "migration_head = $MigrationHead" in BUILD
    assert "payload" in BUILD
    assert "Get-FileHash -LiteralPath $installerPath -Algorithm SHA256" in BUILD
    assert "SHA256SUMS.txt" in BUILD


def test_approved_multiresolution_icon_is_wired_through_windows_surfaces():
    icon = ROOT / "assets" / "branding" / "wealthos-app-icon.ico"
    data = icon.read_bytes()
    reserved, image_type, count = struct.unpack_from("<HHH", data)
    assert (reserved, image_type, count) == (0, 1, 9)
    sizes = {
        (data[6 + index * 16] or 256, data[7 + index * 16] or 256)
        for index in range(count)
    }
    assert sizes == {(size, size) for size in (16, 20, 24, 32, 40, 48, 64, 128, 256)}
    assert "--icon 'assets\\branding\\wealthos-app-icon.ico'" in BUILD
    assert "--add-data 'assets\\branding\\wealthos-app-icon.ico;assets\\branding'" in BUILD
    assert "SetupIconFile=..\\assets\\branding\\wealthos-app-icon.ico" in INSTALLER
    assert 'IconFilename: "{app}\\{#AppExeName}"' in INSTALLER
