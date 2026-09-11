# Lab 02 Result

The baseline fake service accepts malformed/unauthorized payloads and commits duplicate logical writes. The gateway blocks malformed and unauthorized calls before mutation and deduplicates repeated calls sharing an idempotency key while preserving valid writes.

Local verification before publication: Lab 01 + Lab 02 tests pass together.

This does **not** yet solve ambiguous timeout-after-commit behavior. Lab 03 isolates that failure mode because ordinary gateway-level idempotency propagation is not enough to decide whether retry is safe.
