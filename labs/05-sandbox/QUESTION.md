# Lab 05 — Cross-run environment isolation

## Architecture question

When does environment isolation materially improve agent reliability and eval validity?

## Failure injection

Trial A leaves `result.txt=PASS`. Trial B is intentionally broken and produces no output.

## Baseline

Both trials share one mutable workspace. Trial B's verifier sees Trial A's stale output and incorrectly passes.

## Treatment

Each trial receives a fresh workspace cloned from the same template and is destroyed after the trial. Network intent, output-byte limit, and path boundary are explicit policy rather than hidden assumptions.

## Boundary

This lab proves **workspace isolation**, not hostile-code containment. A disposable directory is sufficient when code is trusted and the main risk is cross-run contamination. Generated/untrusted code that can spawn processes, access devices, escape paths, or reach the network needs an OS/container/VM sandbox with enforceable capabilities.
