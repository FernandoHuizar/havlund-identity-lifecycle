# Havlund Pharma Identity Lifecycle Design

## Company
Havlund Pharma is a made-up Danish pharma company with a US site near Sacramento. This lab uses 15 fake employees to test the process. A real rollout would cover the whole company.

The HR system decides who works here and what job they have. Okta is the main identity system. Active Directory runs the on-site systems like lab computers and file shares. Entra ID runs Microsoft 365.

## Problem
Right now IT creates and removes accounts by hand from HR emails. New hires wait days for access. People who leave keep access too long. Nobody can easily show who has access to what.

That matters more in pharma. GDPR, NIS2, and FDA 21 CFR Part 11 all expect a company to control access and keep a record of changes. This lab doesn't claim compliance. It shows the kind of controls those rules look for.

## Scope
- HR system: 15 fake employees
- Okta: up to 9 active users at a time (free plan limit)
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