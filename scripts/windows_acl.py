import json
import os
import subprocess
from pathlib import Path


SYSTEM_SID = "S-1-5-18"
ADMINISTRATORS_SID = "S-1-5-32-544"

_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
$path = $env:WEALTHOS_ACL_PATH
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$acl = [System.IO.Directory]::GetAccessControl($path)
$acl.SetAccessRuleProtection($true, $false)
foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleSpecific($rule) }
$acl.SetOwner($identity.User)
$inherit = [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
$propagate = [System.Security.AccessControl.PropagationFlags]::None
$allow = [System.Security.AccessControl.AccessControlType]::Allow
foreach ($sidText in @($identity.User.Value, 'S-1-5-18', 'S-1-5-32-544')) {
  $sid = [System.Security.Principal.SecurityIdentifier]::new($sidText)
  $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, [System.Security.AccessControl.FileSystemRights]::FullControl, $inherit, $propagate, $allow)
  [void]$acl.AddAccessRule($rule)
}
[System.IO.Directory]::SetAccessControl($path, $acl)
$verified = [System.IO.Directory]::GetAccessControl($path)
$ownerSid = ([System.Security.Principal.NTAccount]$verified.Owner).Translate([System.Security.Principal.SecurityIdentifier]).Value
$rules = @($verified.Access | ForEach-Object {
  [pscustomobject]@{
    sid = $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    type = $_.AccessControlType.ToString()
    rights = [int]$_.FileSystemRights
    inherited = $_.IsInherited
  }
})
[pscustomobject]@{ current = $identity.User.Value; owner = $ownerSid; rules = $rules } | ConvertTo-Json -Depth 4 -Compress
"""

_VERIFY_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
$path = $env:WEALTHOS_ACL_PATH
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$verified = [System.IO.Directory]::GetAccessControl($path)
$ownerSid = ([System.Security.Principal.NTAccount]$verified.Owner).Translate([System.Security.Principal.SecurityIdentifier]).Value
$rules = @($verified.Access | ForEach-Object {
  [pscustomobject]@{
    sid = $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    type = $_.AccessControlType.ToString()
    rights = [int]$_.FileSystemRights
    inherited = $_.IsInherited
  }
})
[pscustomobject]@{ current = $identity.User.Value; owner = $ownerSid; rules = $rules } | ConvertTo-Json -Depth 4 -Compress
"""


def _validate_evidence(output: str) -> None:
    try:
        evidence = json.loads(output.strip())
        rules = evidence["rules"]
        if isinstance(rules, dict):
            rules = [rules]
        allowed = {evidence["current"], SYSTEM_SID, ADMINISTRATORS_SID}
        if evidence["owner"] != evidence["current"] or not rules:
            raise ValueError
        if any(rule["sid"] not in allowed or rule["type"] != "Allow" or rule["inherited"] for rule in rules):
            raise ValueError
        if not any(rule["sid"] == evidence["current"] and (rule["rights"] & 2032127) == 2032127 for rule in rules):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("The WealthOS data permissions failed verification.") from error


def secure_and_verify_directory(path: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("WealthOS local data permissions require Windows.")
    environment = os.environ.copy()
    environment["WEALTHOS_ACL_PATH"] = str(path)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _POWERSHELL],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("The WealthOS data permissions could not be secured.")
    _validate_evidence(result.stdout)


def verify_directory_acl(path: Path) -> None:
    environment = os.environ.copy()
    environment["WEALTHOS_ACL_PATH"] = str(path)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _VERIFY_POWERSHELL],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("The WealthOS data permissions could not be verified.")
    _validate_evidence(result.stdout)
