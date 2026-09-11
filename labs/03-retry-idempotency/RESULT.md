# Lab 03 Result

Injected `commit -> response loss` makes blind retry perform two physical writes for one logical operation. The treatment performs one physical write, detects the ambiguous outcome, and recovers it through read-after-write reconciliation using the same idempotency key.

Injected pre-commit failure is different: no write exists, so bounded retry recovers safely and produces one physical write.

Decision boundary: retry is sufficient only when failure semantics establish that the side effect did not commit. Ambiguous outcomes require idempotency plus reconciliation.
