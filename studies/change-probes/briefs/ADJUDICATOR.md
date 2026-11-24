# Adjudicator brief: did the gate block for the team's own reason?

You are given one finished gate that blocked a change, and the sealed answer for that change:
the regression the project's own team later fixed. Your only job is to say whether one of the
gate's blocking findings is that same regression.

## What you are given

- `<case>/key_row.json`: the answer row. It names the introducing change, the fixing change, the
  witness test (a test that passes before the change, fails after it and passes after the fix)
  and a short description of what broke.
- `<case>/verdict.json`: the gate's decision, with its list of blocking findings.
- `<case>/findings_final.json` and `<case>/verdicts.json`: the full text of each finding.
- `<case>/probes/`: the probe file behind each finding.

Read nothing else. Do not run anything. Do not look at any repository, the web or git history.

## How to judge

A blocking finding matches when it shows the same lost behaviour as the witness: the same entry
point or feature, failing in the same way, for the same underlying cause. The wording and the
exact inputs may differ.

It does not match when:

- it is a different behaviour change in the same commit, even in the same file;
- it only touches the same function but fails for a different cause;
- it is a consequence so indirect that fixing the team's regression would not make the probe
  pass again.

If the fix described in the key row would plainly make the probe pass again, that is a match.
If you cannot tell, answer `false` and say what is missing. Do not give the benefit of the doubt.

## What to write

Write `<case>/adjudication.json`:

```json
{
  "gate_id": "<id>",
  "match": true,
  "matching_probe": "<probe file name or null>",
  "reason": "<two sentences: what the team's regression was, and why this finding is or is not it>"
}
```

Final message: one line: `match` or `no match`, and the probe name if any. Nothing else.
