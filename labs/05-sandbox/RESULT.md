# Lab 05 Result

The shared-workspace baseline creates a deterministic false-positive: Trial B does nothing but still passes because Trial A left the expected artifact behind.

With a fresh workspace per trial, Trial A passes and the broken Trial B fails. Repeating the isolated broken trial five times produces five failures, showing stable verifier behavior without state leakage.

The implementation also makes network, output-size, and path-boundary policy explicit. These checks are intentionally not presented as a security sandbox; stronger isolation is required for untrusted generated code.
