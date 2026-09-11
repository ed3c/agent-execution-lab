# Lab 04 Result

With a hard crash after step 2 of a five-step task:

- in-memory baseline writes steps `0,1,2`, then restart repeats `0,1,2` before finishing `3,4`;
- checkpoint treatment writes `0,1,2`, then restart continues at `3,4` with no repeated committed step;
- a corrupt checkpoint is rejected rather than silently treated as valid progress.

Checkpointing is not justified for short disposable tasks where a full restart is cheaper than persistence/recovery complexity. It becomes useful when repeated work or repeated side effects are materially costly and the task state can be serialized safely.
