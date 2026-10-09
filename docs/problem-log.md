# Problem Log

Problems I ran into while building this lab, why they happened, and how I fixed them.

## 1. Couldn't delete a group in Entra ID
Problem: During tenant cleanup, the IT Support Team group had no delete option in the Entra admin center.

Cause: It was a distribution group created in Microsoft 365. Entra ID can show these groups but doesn't manage them. Exchange does.

Fix: Deleted it from the Microsoft 365 admin center instead.

Lesson: Check a group's type and source before trying to change it. The source tells you which system owns it.

## 2. Azure blocked the subscription
Problem: Creating a pay-as-you-go subscription failed with "user is not eligible for an Azure account."

Cause: Microsoft flagged the account for review on their side. Billing setup and payment method were both fine.

Fix: Sent a review request through aka.ms/AccountReview. Built the Windows Server VM locally so the lab could keep moving.

Lesson: Some blocks come from the vendor, not your configuration. Read the error, confirm your own setup is correct, then go to the right support channel.