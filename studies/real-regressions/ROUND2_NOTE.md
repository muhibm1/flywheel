# Round 2 note: add explored cases to a project that already has its suite

Read `/tmp/rr/blind/WRITER_BRIEF_v2.md` first: its hard rules apply in full. In your project
folder, steps 1 to 4 were already done by an earlier writer: `suite/adapter.py`,
`suite/standing.jsonl`, and each gate's `change.jsonl`. Each gate.json now also names `head_env`.

The model endpoint was upgraded since those cases were written: like a real API it no longer
forces tool calls to be well-formed, it honours `max_tokens` (finish_reason "length") and `stop`
sequences, and it streams text and tool calls in separate chunks.

Do this:
1. Re-run the base smoke for every gate once under the new endpoint
   (`flywheel run --label smoke2 --out smoke2.json --repetitions 1 --concurrency 2`). If a standing
   or change case now fails on base because of the endpoint change or a case bug, repair it with
   the smallest edit and say what you changed and why. Do not otherwise change `standing.jsonl`,
   `change.jsonl` or the adapter's existing behaviour. Never run the head version for this step.
2. Do step 4b of the brief for every gate (explored cases, `diff.jsonl`, up to 4 per gate).
3. Do step 5: rebuild each gate's `dataset.jsonl` (standing, change, diff) and add
   `min_new_error_runs = 2` under `[gate]` in its `flywheel.toml`.
4. Delete any `base.json`, `head.json` or other run files you did not create in this round only if
   they are inside your project folder; never touch anything outside it.

Write files with the Write/Edit tools only. Final reply as the brief says, plus what you repaired
in step 1, and every path outside your project folder that you read.
