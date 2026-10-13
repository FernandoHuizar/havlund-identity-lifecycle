# Problem Log

Problems I ran into while building this lab, why they happened, and how I fixed them.

## 1. Couldn't delete a group in Entra ID
Problem: During tenant cleanup, the IT Support Team group had no delete option in the Entra admin center.

Cause: It was a distribution group created in Microsoft 365. Entra ID can show these groups but doesn't manage them. Exchange does.

Fix: Deleted it from the Microsoft 365 admin center instead.

Lesson: Check a group's type and source before trying to change it. The source tells you which system owns it.

## 2. Azure blocked the subscription
Problem: Creating a pay-as-you-go subscription failed with "Could not create an Azure subscription since user is not eligible for an Azure account."

Cause: Microsoft flagged the account for review on their side. The billing account and payment method were both set up correctly.

Fix: Opened a support request with the Azure Account Review team. They found the block came from their purchase monitoring and removed it. Subscription creation worked after that.

Lesson: Some blocks come from the vendor, not your own setup. Confirm your side is correct first, then use the right support channel instead of working around it.

## 3. Turned off DPoP on the sync app
Problem: Okta turns on DPoP by default for new API service apps. It adds an extra signed proof to every token request, which means a lot more code.

Cause: It's a newer Okta security default, not something the lab needs to prove the joiner, mover, leaver flow.

Fix: Turned off DPoP on the havlund-hr-sync app. The app still signs in with a private key, not a password.

Lesson: In a real company I'd leave DPoP on. For this lab I chose a simpler setup and wrote down why.

## 4. VM create failed on CPU quota
Problem: Creating the VM failed with "QuotaExceeded" for the Standard Bsv2 family in West US 2.

Cause: New pay-as-you-go subscriptions can start with a CPU quota of 0 for some VM families.

Fix: Requested a quota increase to 4 vCPUs in Quotas > Compute. It was approved right away. The create page kept showing the old error until I clicked between tabs to make it validate again.

Lesson: Check quotas for the VM size and region before building. The error's tracking ID shows whether you're looking at a new result or an old one.

## 5. Okta couldn't create users in AD
Problem: Assigning the first group to AD failed with "Access is denied."

Cause: The Okta AD agent runs as the OktaService account, which is a normal domain user. It had no rights to create users in the Havlund OUs.

Fix: Gave OktaService rights only on the Havlund OU with dsacls: create and delete users and groups, and full control over the users and groups inside it. Did not make it a Domain Admin.

Lesson: Service accounts should get only the rights they need, only where they need them.

## 6. AD users got the wrong sign-in name (UPN)
Problem: The first two users were created in AD as name@corp.havlundpharma.com instead of name@havlundpharma.com.

Cause: "Allow Active Directory to source Okta users" was on by default. When the users were assigned to AD, AD became the source of their Okta profile and Okta rewrote their Okta username to the corp domain. That name then went to AD as the UPN. I found this in the Okta System Log ("Update user profile for Okta - changed login").

Fix: Turned off AD sourcing, set the AD username format to "Okta username", fixed the UPN in AD, then set the Okta usernames back. Changing the AD username alone made Okta treat it as a new account and fail with "object already exists."

Lesson: Decide which system is the source of truth before the first assignment. Test with a small group first. Check the System Log before changing more settings.

## 7. Leavers kept their AD groups
Problem: After terminating Freja Mortensen, her AD account was disabled but she was still in HP-QA-Edit and HP-All-Staff in AD, and still in the Quality OU.

Cause: The sync script removes groups in Okta and deactivates the user one second later. Okta Group Push only manages users who are still assigned to AD, so the group removals never reached AD. The Okta System Log showed the group removals and the deactivation, but no group push for her. Okta also doesn't move leavers to another OU.

Fix: Wrote ad/leaver_cleanup.ps1. It runs on the DC, finds disabled users in Havlund > Users, removes all their groups, writes the removed groups into the account description, moves the account to Disabled Users and logs each change. It has a dry-run mode.

Lesson: Disabling an account isn't the whole leaver process. Check what the IAM tool actually does in the target system, not what you expect it to do.