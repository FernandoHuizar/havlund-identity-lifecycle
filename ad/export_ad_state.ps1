<#
export_ad_state.ps1

What it does: Exports every user account under the Havlund OU to a CSV so
drift_check.py can compare AD with HR. It only reads AD and never changes it.
For each account: employee ID, username, sign-in name, on or off, title,
department, which OU it's in, and its HP- groups.

How to run (on HP-DC01):  .\export_ad_state.ps1
Output: C:\HavlundLogs\ad_export.csv. Copy it to reports\ad_export.csv in
the repo on your PC before running the drift check.
#>
$ErrorActionPreference = 'Stop'

$searchBase = "OU=Havlund,DC=corp,DC=havlundpharma,DC=com"
$outFile    = "C:\HavlundLogs\ad_export.csv"
$exportedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$users = Get-ADUser -Filter * -SearchBase $searchBase -Properties employeeID, title, department, memberOf

$rows = foreach ($user in $users) {
    # Only the HP- access groups, by name
    $groups = $user.memberOf | ForEach-Object { (Get-ADGroup $_).Name } |
        Where-Object { $_ -like "HP-*" } | Sort-Object
    # The OU the account sits in (everything after the account's own name)
    $ou = ($user.DistinguishedName -split ",", 2)[1]

    [pscustomobject]@{
        employee_id = $user.employeeID
        username    = $user.SamAccountName
        upn         = $user.UserPrincipalName
        enabled     = $user.Enabled
        title       = $user.Title
        department  = $user.Department
        ou          = $ou
        hp_groups   = $groups -join ";"
        exported_at = $exportedAt
    }
}

New-Item -ItemType Directory -Path (Split-Path $outFile) -Force | Out-Null
$rows | Sort-Object employee_id | Export-Csv $outFile -NoTypeInformation -Encoding UTF8
Write-Output "Exported $($rows.Count) accounts to $outFile"