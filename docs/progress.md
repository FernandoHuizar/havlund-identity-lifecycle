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

## Build order
1. HR export (CSV file, like a Workday or ADP feed)
2. HR to Okta: joiner, mover, leaver
3. Drift check, part 1: HR vs Okta
4. Azure VM, Active Directory, Entra Connect
5. Add AD and Entra ID to the joiner, mover, leaver flows and the drift check
6. Contractor expiry and rehire, README, demo

## Roadmap (detail)
4. AD on HP-DC01: NSG rule (RDP from home IP only), static private IP, RDP in, install AD DS (corp.havlundpharma.com), point VNet DNS at the DC, add havlundpharma.com UPN suffix, create OUs and HP- groups
5. Okta to AD: install Okta AD agent, turn on Create Users with an OU per department, push HP- groups, test joiner/mover/leaver into AD (leavers disabled and moved to Disabled Users)
6. AD to Entra: install Entra Connect Sync or Cloud Sync, sync only the Users OUs, confirm users show as synced from on-premises
7. Drift check part 2: add AD and Entra to drift_check.py
8. Contractor expiry (endDate in Okta, accountExpires in AD) and rehire handling
9. README with Mermaid diagram, demo, cost cleanup (delete rg-havlund-lab when done)
10. Resume bullets and interview walkthrough

## Next step
Add an NSG rule on HP-DC01-nsg allowing RDP (3389) from my home IP only, set the VM's private IP (172.16.0.4) to static, RDP in as hpadmin, then install AD DS and create corp.havlundpharma.com.

## Planned: Azure VM (build order step 4)
- Subscription havlund-lab (Havlund Pharma tenant) with a $10 budget.
- VM HP-DC01 in resource group rg-havlund-lab, West US 2, Windows Server 2022 Datacenter Gen2, Standard_B2s, admin user hpadmin.
- No open inbound ports except RDP from my home IP only. Auto-shutdown every night. No Hybrid Benefit. Check the price before clicking Create.
- The disk costs money even when the VM is off, so only build it when step 4 starts. Delete the whole resource group when the lab is done.

## Later
- Add a custom endDate field in Okta for contractor expiry.
- Handle rehires (the sync script flags them as "Needs review" for now).
- Add my Gmail as a backup on the Okta admin account (it uses my Sierra College email).
- Change the havlund-lab budget alert email to my Gmail.
- Portfolio plan: Project 2 = app onboarding in Okta (SAML, OIDC, SCIM, MFA, runbook). Project 3 = not decided yet: either Entra security (Conditional Access, PIM, break-glass accounts, access reviews; needs a paid P2 month) or a third Okta-focused project. Same Havlund Pharma company, separate repos. Finish this project first.