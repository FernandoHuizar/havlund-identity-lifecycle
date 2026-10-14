# Havlund Pharma Identity Lifecycle Design

## Company
Havlund Pharma is a made-up Danish pharma company with a US site near Sacramento. This lab uses 15 fake employees to test the process. A real rollout would cover the whole company.

The HR system decides who works here and what job they have. Okta is the main identity system. Active Directory runs the on-site systems like lab computers and file shares. Entra ID runs Microsoft 365. The HR system sends a CSV export (sample-data/hr_export.csv), the way Workday or ADP would. The sync scripts read that file.

## Problem
Right now IT creates and removes accounts by hand from HR emails. New hires wait days for access. People who leave keep access too long. Nobody can easily show who has access to what.

That matters more in pharma. GDPR, NIS2, and FDA 21 CFR Part 11 all expect a company to control access and keep a record of changes. This lab doesn't claim compliance. It shows the kind of controls those rules look for.

## Scope
- HR export (CSV): 15 fake employees
- Okta: pilot with the IT and Quality teams (7 users). Leaves 2 open spots for testing new hires. The free plan allows 10 active users and the admin account uses 1.
- Drift check script: compares all 15 HR records against Okta, AD, and Entra ID

## Departments and roles
| Department | Roles |
|---|---|
| IT | IT Support Specialist, System Administrator |
| HR | HR Generalist, HR Manager |
| Quality | QA Specialist, QA Manager |
| R&D | Research Scientist, Lab Technician |

## Access by role
Each role gets these groups automatically on day one.

| Role | Groups |
|---|---|
| IT Support Specialist | HP-All-Staff, HP-IT-Support |
| System Administrator | HP-All-Staff, HP-IT-Support, HP-IT-Admins |
| HR Generalist | HP-All-Staff, HP-HR-Staff |
| HR Manager | HP-All-Staff, HP-HR-Staff |
| QA Specialist | HP-All-Staff, HP-QA-Edit |
| QA Manager | HP-All-Staff, HP-QA-Approve |
| Research Scientist | HP-All-Staff, HP-RD-Data, HP-Lab-Computers |
| Lab Technician | HP-All-Staff, HP-Lab-Computers |

## Access rules
- Nobody can be in HP-QA-Edit and HP-QA-Approve at the same time. The person who writes a quality record can't approve it.
- Contractors also get HP-Contractors. Their account turns off on their end date.
- When someone leaves, all access is removed the same day.
- When someone changes jobs, old groups are removed and new ones added. No leftover access.

## Field map
How each HR field shows up in the other systems.

| HR field | Okta | Active Directory | Entra ID |
|---|---|---|---|
| employee_id | employeeNumber | employeeID | employeeId |
| first_name | firstName | givenName | givenName |
| last_name | lastName | sn | surname |
| job_title | title | title | jobTitle |
| department | department | department | department |
| manager_id | managerId | manager | manager |
| employee_type | userType | employeeType | employeeType |
| status | user status | enabled or disabled | accountEnabled |
| end_date | endDate (custom field, added later) | accountExpires | synced from AD |

## Username rule
- Login and email: first.last@havlundpharma.com, all lowercase.
- If the name is taken, add a number (anna.jensen2).

## Where users go in AD
Everything goes under one company OU, Havlund, in corp.havlundpharma.com:
- Havlund > Users > IT
- Havlund > Users > HR
- Havlund > Users > Quality
- Havlund > Users > R&D
- Havlund > Disabled Users (leavers move here)
- Havlund > Groups (HP- groups)

## How users get into AD
- Group rules put people into AD-Users-IT, AD-Users-Quality, AD-Users-HR or AD-Users-RD based on their HR department.
- Each AD-Users group is assigned to AD with its department OU. These groups only decide the AD account and OU. They don't give access and are never pushed to AD.
- Okta is the source of truth. AD is not allowed to source Okta profiles.
- The Okta agent's service account only has rights on the Havlund OU.

## How users get into Entra ID
- Entra Cloud Sync copies users from AD to Entra ID. A small agent on the DC does the work. The settings live in the Entra admin center.
- Why Cloud Sync and not Connect Sync: it's Microsoft's recommended path for most companies, the agent is light, and it covers what Havlund needs. Connect Sync still makes sense for very large directories or custom sync rules.
- Scope: Havlund > Users (IT, HR, Quality, R&D) and Havlund > Disabled Users.
- Leavers: Disabled Users is in scope on purpose. A leaver's Entra account is disabled, not deleted, so the audit trail stays. Deleting an account should be a separate, approved step after a retention period.
- Source of truth: once synced, AD owns these users. Changes start in HR, go through Okta to AD, then to Entra.
- Accounts: the agent runs as a gMSA, so AD manages its password. It signs in to Entra with a cloud-only account that only has the Hybrid Identity Administrator role.

## Note
Some fields may not pass through every system the way this table shows. Each one gets tested during the build. Anything that doesn't work goes in the problem log with the fix.