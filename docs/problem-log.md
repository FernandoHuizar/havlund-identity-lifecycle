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