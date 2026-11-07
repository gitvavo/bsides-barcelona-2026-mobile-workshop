# Mockapp points-transfer IPC workshop

This is an intentionally vulnerable fictional Android loyalty app. Test only
on the isolated workshop network.

## Intended behavior

The dashboard's Send points button asks for a friend username, amount and
confirmation. Without a login, the dashboard opens the login activity.

## IPC issue

The dashboard is exported and also serves as the normal launcher. When the
user is logged in it trusts `transfer_to_user`, `transfer_points` and
`auto_send` supplied through an external Intent.

```
adb -e shell am start -n com.mockapp.loyalty/.DashboardActivity --es transfer_to_user bob --ei transfer_points 10000 --ez auto_send true
```

## Backend issue

The transfer API validates authentication, recipient and positive amount but
intentionally does not check the sender's current balance. Repeated transfers
can make the sender negative while crediting the chosen recipient.

Reproduce using alice (420 points) and bob (850 points). After a transfer of
10,000 points: alice -9,580; bob 10,850. Repeat to demonstrate overdrafts.

For mitigation, validate and authorize the sender's action through a trusted
app flow, and enforce a sufficient-balance condition transactionally on the
server. Do not treat Intent extras as proof of user consent.
