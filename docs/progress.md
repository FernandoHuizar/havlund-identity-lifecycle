# Build Progress

Where the lab stands right now. Updated as each part is finished.

## Done
- Repo set up with folders for each part of the lab
- Design doc: company, problem, scope, roles, access by role, field map, username rule, AD layout
- Problem log started
- Entra tenant cleaned up and renamed to Havlund Pharma
- havlundpharma.com added and verified as the primary domain
- Azure budget alert set to $10 a month
- Fake HR export (CSV) with 15 employees
- Azure block removed by Microsoft. Subscription havlund-lab created with a $10 budget.
- Okta service app havlund-hr-sync created (private key sign-in, 4 scopes, Org Admin role)
- Okta sign-in script working (scripts/okta_client.py signs in with the private key and lists users)
- Access rules config (okta/access_rules.json) and 9 HP- groups created in Okta by script (safe to rerun)
- Joiner in Okta working: hr_to_okta.py created the 7 pilot users with the right groups, matching on employee ID (safe to rerun)
- Mover in Okta working: promoted David Kim (QA Specialist to QA Manager). Script updated his title, removed HP-QA-Edit first, then added HP-QA-Approve
- Leaver in Okta working: terminated Jordan Reyes in HR. Script removed his groups and deactivated his account. Okta System Log shows each step with a time stamp
- Drift check part 1 working: drift_check.py compares HR with Okta and writes reports/drift_report.csv. Admin account listed as an approved exception
- Drift check tested: made 3 problems by hand in Okta (SOD conflict, account outside HR, leaver turned back on). Drift check caught all 4 findings, sync fixed the HR-owned ones, deactivated the outside account by hand, drift check came back clean
- Azure VM HP-DC01 created in rg-havlund-lab (smalldisk Windows Server 2022, Standard_B2ls_v2, Standard SSD, NSG with no inbound rules yet, auto-shutdown 1 AM)
- HP-DC01 set up as the first domain controller for corp.havlundpharma.com (NetBIOS name HAVLUND). RDP allowed from my home IP only, private IP 172.16.0.4 set to static
- VNet DNS pointed at the DC, havlundpharma.com UPN suffix added, OUs created under Havlund (Users by department, Disabled Users, Groups)
- Okta AD agent installed on HP-DC01 and connected to corp.havlundpharma.com (OktaService account, OU scope limited to Havlund users, disabled users and groups)
- Okta to AD joiner working for IT: Mette Nielsen and Priya Shah created in Havlund > Users > IT with the right UPN, employee ID, title, department and employee type
- Quality joiner into AD working (4 users in Havlund > Users > Quality). All 9 HP- groups pushed from Okta to Havlund > Groups with the right members. Nobody is in both QA groups in AD
- Mover into AD working: promoted Emily Carter (QA Specialist to QA Manager) in the HR export. The sync script swapped her Okta groups and AD followed on its own: title updated, HP-QA-Edit removed, HP-QA-Approve added
- Leaver into AD working: terminated Freja Mortensen in the HR export. Okta disabled her AD account, then ad/leaver_cleanup.ps1 removed her AD groups, noted them in her description and moved her to Disabled Users
- Leaver cleanup tested as a scheduled task under a gMSA. Group removal worked, account move needs one more permission. Task disabled, cleanup runs by hand for now
- Picked Entra Cloud Sync over Connect Sync (Microsoft's recommended path, light agent that fits the 4 GB lab server, covers OU scope, password hash sync and field mapping)
- Created a cloud-only sync admin (hp-sync-admin) on the onmicrosoft.com domain with only the Hybrid Identity Administrator role and MFA
- Installed the Cloud Sync agent on HP-DC01. It runs as a gMSA (provAgentgMSA) that the installer created
- Decided to sync Disabled Users too, so leavers are disabled in Entra instead of deleted
- Created the Cloud Sync config: scoped to the 4 department OUs, Disabled Users and Groups. Password hash sync on, failure alerts on, accidental delete limit lowered from 500 to 5
- Tested before turning sync on (provision on demand): Mette Nielsen (joiner) created with the right employee ID, title and department. Freja Mortensen (leaver) created disabled, with her removed groups in the description. hpadmin blocked by scope
- AD to Entra working: 7 users synced (5 enabled, 2 disabled leavers) and all 9 HP- groups. HP-QA-Approve has the 3 QA Managers and HP-QA-Edit is empty, so no SOD conflict in Entra. Admin and service accounts stayed out
- Drift check part 2 working: drift_check.py now checks Okta, AD and Entra against HR with the same rules, plus a new AD check for leavers left in a department OU. Entra is read with a read-only app (havlund-drift-check, certificate sign-in, User.Read.All and GroupMember.Read.All). AD is read from an export made on the DC (ad/export_ad_state.ps1). First run: 3 findings, test.leaver in AD and Entra and alex.vendor in Okta (no employee ID)
- Handled the drift findings: deleted test.leaver in AD (Entra moved it to Deleted users after sync) and the alex.vendor test account in Okta. Both were test accounts with no HR record or owner
- Found sync quarantined after the nightly VM shutdown (problem 9). Restarted it and the drift check came back clean across Okta, AD and Entra
- Tested drift check part 2 on purpose: changed AD by hand (David Kim added to HP-QA-Edit, Freja Mortensen turned back on, Sofie Larsen's title changed). The check found all 8 findings, each in both AD and Entra, and Okta stayed clean. Fixed AD to match HR. New sample report saved
- Contractor expiry working: hr_to_okta.py now treats anyone whose end date has passed as a leaver, even if HR still says Active. Tested with Priya Shah (end date set to 2026-10-13, status left Active): groups removed and account turned off in Okta, AD disabled, leaver cleanup moved her to Disabled Users, Entra disabled after sync
- Rehire working: if a turned-off person is Active in HR with a start date after their account was turned off, the script turns the same account back on with only the new job's groups. An older start date goes to Needs review, a future start date waits. Tested with Jordan Reyes: same Okta account, new AD account in the IT OU with HP-All-Staff and HP-IT-Support, synced to Entra
- Drift check uses the same end date rule. After the test it came back clean across Okta, AD and Entra (Entra 9 accounts with Jordan)
- README written: business problem, Mermaid diagram, 30-second summary, lifecycle table, drift checks, results I actually ran, top problems, how to run.

## Build order
1. HR export (CSV file, like a Workday or ADP feed)
2. HR to Okta: joiner, mover, leaver
3. Drift check, part 1: HR vs Okta
4. Azure VM, Active Directory, Entra Connect
5. Add AD and Entra ID to the joiner, mover, leaver flows and the drift check
6. Contractor expiry and rehire, README, demo

## Roadmap (detail)
4. AD on HP-DC01: NSG rule (RDP from home IP only), static private IP, RDP in, install AD DS (corp.havlundpharma.com), point VNet DNS at the DC, add havlundpharma.com UPN suffix, create OUs
5. Okta to AD: install Okta AD agent, turn on Create Users with an OU per department, push HP- groups into the Havlund > Groups OU, test joiner/mover/leaver into AD (leavers disabled and moved to Disabled Users)
6. AD to Entra: Entra Cloud Sync, sync the 4 department OUs and Disabled Users, check field mapping, confirm users show as synced from on-premises
7. Drift check part 2: add AD and Entra to drift_check.py
8. Contractor expiry and rehire handling (done: end date in the HR export drives the leaver flow, rehires reuse the same account)
9. README with Mermaid diagram (done). Cost cleanup (delete rg-havlund-lab) when I'm done with the lab

## Next step
Project 1 is finished. Next is Project 2 (havlund-app-access). Keep rg-havlund-lab until Project 3 is done, target early December 2026. Items under Later are open questions, not required.

## Later
- Add my Gmail as a backup on the Okta admin account (it uses my Sierra College email).
- Change the havlund-lab budget alert email to my Gmail.
- Portfolio plan: see START-HERE.md in the havlund-labs folder. Project 2 = app access (Salesforce through Okta, ServiceNow requests, access review). Project 3 = privileged access with Delinea.
- Leaver root-cause fix: hr_to_okta.py removes groups and deactivates the user 1 second later, so the removals never reach AD. Fix: remove the groups, wait until the push reaches AD (about 2 minutes), then deactivate. Keep leaver_cleanup.ps1 for the OU move, which Okta can't do, and as a safety net.
- Leaver cleanup scheduled task: svc-leaver needs one more right to move accounts to Disabled Users. Task is disabled for now.
- Map the AD manager field (AD needs the manager's AD path, not their employee ID).
- Find out why Okta users went from Pending user action to Active when they were assigned to AD.
- Find out why Okta made 107 "accounts need deprovisioning" tasks before clearing them. Clue: Priya's deactivation on 2026-10-14 logged "Deprovision user from external application" with a DeprovisionTask on the AD app.
- Turn on LDAPS for the Okta AD agent (skipped in the lab).
- Test the duplicate-name rule: the second Emily Carter (1014, R&D) is outside the pilot, so emily.carter2 was never made.
- Have hr_to_okta.py save a run log (CSV of every change), like leaver_cleanup.ps1 does.
- Add a simple access review report: each manager's people and their groups, for sign-off.
- Use one time zone (UTC) for dates everywhere. The leaver cleanup now writes UTC dates and says so. Freja's older note (disabled 2026-10-13, HR end date 2026-10-12) shows why.
- Security defaults are off in Entra, so synced users can sign in to Microsoft 365 with only a password. Fix with sign-in security (Conditional Access).
- Check the Cloud Sync status at the start of each lab session. The nightly VM shutdown pauses it.
- Okta pushes group changes to AD about 2 minutes after the account is created. Run the AD export a few minutes after hr_to_okta.py, or the drift check shows false MISSING_ACCESS findings.