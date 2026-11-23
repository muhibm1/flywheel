# Brief: veto test checks that are not required behaviour

You review test cases written for an AI-agent project's regression gate. Each "explored" case was
written by someone who ran two versions of the agent. Your job is to stop checks that merely
prefer one version's behaviour over another when that behaviour is not actually required.

Your project folder is `/tmp/rr/blind/<project>/`. For each gate folder `<project>-gN` read ONLY:
`diff.jsonl` (the explored cases), and the check functions they use in `suite/adapter.py`
(and the gate's `adapter.py` shim). Do NOT read `change.diff`, `change-message.txt`, any smoke or
run output, `gate.json`, anything under `/root`, `/home/user/flywheel/studies`, or other projects.
No git, no network. You may read the base README or docs named in a case's citation to confirm
the quote exists.

For each explored case decide KEEP or DROP:
- KEEP when a reasonable user of this agent framework would agree the checked behaviour is
  required: the task gets done, the answer is right, the agent does not crash, a documented
  option does what its docs or the cited source say.
- DROP when the check depends on an incidental detail (exact wording, a specific number of
  steps or calls, an internal message format, a particular order) that a correct agent could
  reasonably do differently, or when the citation does not support it.

Write `<gate>/veto.json`: `[{"id": ..., "decision": "KEEP"|"DROP", "reason": one sentence}]`.
Then rewrite `<gate>/diff.jsonl` without the dropped cases (Write tool only), keep the original
as `<gate>/diff.prevote.jsonl`, and rebuild `<gate>/dataset.jsonl` as standing.jsonl, then
change.jsonl, then the kept diff.jsonl.

Final reply: per gate, kept and dropped counts, and the paths you read.
