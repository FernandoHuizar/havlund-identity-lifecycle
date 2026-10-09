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

Fix: Opened a support request with the Azure Account Review team. Waiting on their reply.

Lesson: Some blocks come from the vendor, not your own setup. Confirm your side is correct first, then use the right support channel instead of working around it.