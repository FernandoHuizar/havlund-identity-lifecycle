# Problem Log

Problems I ran into while building this lab, why they happened, and how I fixed them.

## 1. Couldn't delete a group in Entra ID
During tenant cleanup, the IT Support Team group had no delete option in the Entra admin center.

It turned out to be a distribution group created in Microsoft 365. Entra ID can show these groups but doesn't manage them. Exchange does.

I deleted it from the Microsoft 365 admin center instead.

What I learned is to check a group's type and source before trying to change it. The source tells you which system owns it.

## 2. Azure blocked the subscription
Creating a pay-as-you-go subscription failed with "Could not create an Azure subscription since user is not eligible for an Azure account."

Microsoft had flagged the account for review on their side. The billing account and payment method were both set up correctly.

I opened a support request with the Azure Account Review team. They found the block came from their purchase monitoring and removed it, and subscription creation worked after that.

Some blocks come from the vendor, not your own setup. I confirm my side is correct first, then use the right support channel instead of working around it.

## 3. Turned off DPoP on the sync app
Okta turns on DPoP by default for new API service apps. It adds an extra signed proof to every token request, which means a lot more code.

It's a newer Okta security default, and the lab doesn't need it to prove the joiner, mover, leaver flow.

I turned off DPoP on the havlund-hr-sync app. The app still signs in with a private key, not a password.

In a real company I'd leave DPoP on. For this lab I chose a simpler setup and wrote down why.

## 4. VM create failed on CPU quota
Creating the VM failed with "QuotaExceeded" for the Standard Bsv2 family in West US 2.

New pay-as-you-go subscriptions can start with a CPU quota of 0 for some VM families.

I requested a quota increase to 4 vCPUs in Quotas > Compute, and it was approved right away. The create page kept showing the old error until I clicked between tabs to make it validate again.

Now I check quotas for the VM size and region before building. The error's tracking ID shows whether you're looking at a new result or an old one.

## 5. Okta couldn't create users in AD
Assigning the first group to AD failed with "Access is denied."

The Okta AD agent runs as the OktaService account, which is a normal domain user. It had no rights to create users in the Havlund OUs.

I gave OktaService rights only on the Havlund OU with dsacls. That covers creating and deleting users and groups, and full control over the users and groups inside it. I didn't make it a Domain Admin.

Service accounts should get only the rights they need, only where they need them.

## 6. AD users got the wrong sign-in name (UPN)
The first two users were created in AD as name@corp.havlundpharma.com instead of name@havlundpharma.com.

"Allow Active Directory to source Okta users" was on by default. When the users were assigned to AD, AD became the source of their Okta profile, and Okta rewrote their Okta username to the corp domain. That name then went to AD as the UPN. I found this in the Okta System Log ("Update user profile for Okta - changed login").

I turned off AD sourcing, set the AD username format to "Okta username", fixed the UPN in AD, then set the Okta usernames back. Changing the AD username alone made Okta treat it as a new account and fail with "object already exists."

Decide which system is the source of truth before the first assignment. Test with a small group first, and check the System Log before changing more settings.

## 7. Leavers kept their AD groups
After I terminated Freja Mortensen, her AD account was disabled but she was still in HP-QA-Edit and HP-All-Staff in AD, and still in the Quality OU.

The sync script removes groups in Okta and deactivates the user one second later. Okta Group Push only manages users who are still assigned to AD, so the group removals never reached AD. The Okta System Log showed the group removals and the deactivation, but no group push for her. Okta also doesn't move leavers to another OU.

I wrote ad/leaver_cleanup.ps1. It runs on the DC, finds disabled users in Havlund > Users, removes all their groups, writes the removed groups into the account description, moves the account to Disabled Users and logs each change. It has a dry-run mode.

Disabling an account isn't the whole leaver process. Check what the IAM tool actually does in the target system, not what you expect it to do.

After that I set the cleanup up as a scheduled task under a gMSA (svc-leaver) with rights only on the Havlund OUs. Removing groups and writing the description worked, but the move to Disabled Users failed on a missing permission and the script still said it succeeded. I added $ErrorActionPreference = 'Stop' so errors stop the script, disabled the task, and run the cleanup by hand for now.

It happened again on 2026-10-14 when Priya Shah's contract ended. Her AD account was disabled but still in 3 groups and in the IT OU. The drift check flagged EXTRA_ACCESS and LEAVER_NOT_MOVED, and the cleanup fixed both. This is a known gap in how Okta handles leavers, so the cleanup stays part of the process.

## 8. Sync agent couldn't sign in to Entra
The Cloud Sync setup wizard couldn't load the Microsoft sign-in page. A pop-up said the content was blocked by Internet Explorer Enhanced Security Configuration.

Windows Server turns this setting on for admins by default. It blocks most websites in the server's built-in browser, including the sign-in page the wizard uses.

I turned it off for admins in Server Manager, reopened the wizard (it kept the old setting until restarted), signed in, then turned it back on.

Server safety settings can block setup tools. Turn them off only for the task, then turn them back on.

## 9. Sync stopped overnight and a deleted account stayed in Entra
After I deleted test.leaver in AD, the drift check still found it in Entra. Entra showed the sync as "Provisioning quarantined" with the error HybridIdentityServiceNoActiveAgents. Nothing had synced for about 20 hours.

The lab DC shuts down at 1 AM to save money. With the server off, Entra couldn't reach the sync agent and paused sync. It stayed paused after the server came back on.

I checked the agent service on the DC (running), then clicked Restart provisioning in Entra. The status went back to Healthy, test.leaver moved to Deleted users, and the drift check came back clean.

When sync stops, leavers keep their cloud access. The failure alert email fired overnight and the drift check caught the gap. Check that sync is healthy, don't assume it's running.
