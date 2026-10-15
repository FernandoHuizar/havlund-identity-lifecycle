# Lab vs real world

Shortcuts I took in this lab and what a real company would do instead.

| In this lab | In a real company |
|---|---|
| HR data is a CSV file | The HR system (Workday, SuccessFactors) feeds the identity system through a connector or API |
| I run the sync script by hand | It runs on a schedule and alerts someone when it fails |
| Okta pilot with 7 users (free plan limit) | Everyone is in scope |
| DPoP turned off on the sync app | Left on |
| Leaver cleanup in AD runs by hand | Runs on a schedule right after the HR change |
| Okta AD agent and Cloud Sync agent on the domain controller, one of each | Their own servers, 2 or more agents each, LDAPS turned on |
| Disabled accounts are kept forever | Deleted after a set retention period, with the approval on record |
| Okta keeps logs 90 days, Entra 7 to 30 days | Logs go to a SIEM and are kept for years |
| Drift check runs by hand and writes a CSV | Runs on a schedule, each finding becomes a ticket with an owner |
| Access exceptions are an entry in a JSON file | A ticket with an approver, a reason and an end date |
| Sync failure alerts go to my own email | A shared IAM team mailbox or ticket queue |
| No MFA or sign-in rules for users in Okta or Entra | MFA required for everyone (covered in my next project) |
| The DC shuts down every night to save money, which pauses sync | Sync servers stay on, with 2 or more agents so sync keeps running if one goes down |
| Cloud Sync runs every 20 minutes | Same, so urgent leavers are also disabled in Entra directly and their sessions revoked right away |
| Rehires are spotted by comparing the HR start date with the date the account was turned off | HR sends a rehire flag, and access for a returning person may need a manager's approval |
| The AD export runs by hand, so it can be a few minutes behind Okta | The check reads AD directly at the time it runs |