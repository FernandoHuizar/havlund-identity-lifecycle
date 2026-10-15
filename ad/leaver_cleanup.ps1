<#
leaver_cleanup.ps1

What it does: Finds disabled accounts still in Havlund > Users, removes all
their groups, notes the removed groups in the account description, and moves
the account to Havlund > Disabled Users. Okta disables leavers in AD but
doesn't remove their AD groups or move them, so this finishes the job.

How to run (on HP-DC01 as a domain admin):
  .\leaver_cleanup.ps1 -DryRun   (shows what would happen)
  .\leaver_cleanup.ps1           (makes the changes)
Output: prints each change and adds a line per user to C:\HavlundLogs\leaver_cleanup.csv
#>
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'

$usersOU    = "OU=Users,OU=Havlund,DC=corp,DC=havlundpharma,DC=com"
$disabledOU = "OU=Disabled Users,OU=Havlund,DC=corp,DC=havlundpharma,DC=com"
$logFile    = "C:\HavlundLogs\leaver_cleanup.csv"
$today      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")  # UTC, same as the other logs

# Disabled accounts that haven't been cleaned up yet
$leavers = Get-ADUser -Filter 'Enabled -eq $false' -SearchBase $usersOU -Properties memberOf
if (-not $leavers) { Write-Output "No disabled users found in Havlund > Users."; return }

foreach ($user in $leavers) {
    $groups = $user.memberOf | ForEach-Object { (Get-ADGroup $_).Name }
    $groupList = if ($groups) { $groups -join ", " } else { "none" }

    if ($DryRun) {
        Write-Output "Would clean up: $($user.SamAccountName) (remove: $groupList, move to Disabled Users)"
        continue
    }

    # Remove every group, then record what was removed, then move the account
    foreach ($groupDN in $user.memberOf) {
        Remove-ADGroupMember -Identity $groupDN -Members $user -Confirm:$false
    }
    Set-ADUser $user -Description "Disabled $today (UTC). Groups removed: $groupList"
    Move-ADObject -Identity $user.DistinguishedName -TargetPath $disabledOU

    New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null
    [pscustomobject]@{ date = $today; user = $user.SamAccountName; groups_removed = $groupList } |
        Export-Csv $logFile -Append -NoTypeInformation
    Write-Output "Cleaned up: $($user.SamAccountName) (removed: $groupList, moved to Disabled Users)"
}