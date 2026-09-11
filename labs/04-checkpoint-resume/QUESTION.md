# Lab 04 — Checkpoint + resume

## Architecture question

When does externalized state justify checkpoint/resume complexity?

## Failure injection

A separate worker process is terminated with `os._exit(99)` after deterministic step N. This is a hard process death: normal exception/finally recovery does not run.

## Baseline

All progress is in memory. Restart begins at step 0.

## Treatment

After each committed step, persist a checksummed checkpoint with `next_step`, using temp-file + atomic replace. Restart validates the checkpoint and resumes from the next uncommitted step.

## Boundary

This lab injects failure **after** side effect + checkpoint are committed. Crash between external side effect and checkpoint is an ambiguous outcome and must use Lab 03's idempotency/reconciliation mechanism rather than pretending checkpointing creates exactly-once execution.
