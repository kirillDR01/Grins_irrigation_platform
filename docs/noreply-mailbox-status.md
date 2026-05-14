# `noreply@grinsirrigation.com` Mailbox Status

## Context

`noreply@grinsirrigation.com` is the `TRANSACTIONAL_SENDER` address used by
`EmailService._get_sender` for transactional emails (welcome, confirmation,
renewal notices, estimate sends, etc.). It is **only** used as a `From:`
address — customers should not reply to it.

The office's audit trail for outbound customer email no longer depends on
this mailbox: per Cluster H §12, every customer-facing email is now BCC'd
to `info@grinsirrigation.com` (controlled by `OUTBOUND_BCC_EMAIL` in
prod). The `noreply@` mailbox status is therefore informational rather
than load-bearing — but we still want to confirm whether it accepts mail,
discards it, or bounces, in case a customer replies anyway.

## Verification Checklist (Google Workspace admin)

- [ ] Search Workspace admin → Users for `noreply@grinsirrigation.com`.
      Is it a real user account, a Group, a routing alias, or unowned?
- [ ] If a real user: who owns the inbox? Is anyone reading it?
- [ ] If a Group: who are the members? What's the delivery setting
      (deliver / discard / forward)?
- [ ] If an alias: where does mail route to? Is the destination read?
- [ ] If unowned: confirm whether inbound mail bounces, is silently
      dropped, or gets accepted into limbo. Document the bounce text if
      any.
- [ ] Send a test reply from a Gmail account to `noreply@grinsirrigation.com`
      and observe the result (bounce vs. silent accept).
- [ ] Decide: do we want it to auto-reply with "this address is not
      monitored — please email info@ or call 952-818-1020"? Or just
      silently discard?

## Findings (filled in by Kirill)

<!-- Drop the verification results here after running through the checklist. -->

_Pending verification._
