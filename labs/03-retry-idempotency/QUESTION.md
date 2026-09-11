# Lab 03 — Retry vs idempotency + reconciliation

## Architecture question

When is retry sufficient, and when does ambiguous execution require idempotency plus reconciliation?

## Failure classes

1. **Known pre-commit transient failure**: the operation did not commit, so bounded retry is safe.
2. **Ambiguous post-commit timeout**: the operation committed but the response was lost, so blind retry can duplicate the side effect.

## Baseline

Blindly retry both failure classes.

## Treatment

- retry only known pre-commit transient failures;
- attach an idempotency key to writes;
- when the response is ambiguous, read-after-write by idempotency key before deciding to retry.

The experiment intentionally separates retry policy from exactly-once claims: idempotency and reconciliation constrain duplicate logical effects; they do not make the network exactly-once.
