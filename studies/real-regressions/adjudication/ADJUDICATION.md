# Adjudication of the 10 blocked held-out gates

Regressions: did a broken case fail for the team's stated reason?

- agno-g1: yes. Both broken cases (diff-g1-multi-server-params-no-headers, chg-g1-multi-mcp-provider) combine a header_provider with MultiMCPTools, and head.log shows connection failures that base.log lacks. The exact TypeError text is not logged, so this is inferred from the diff.
- browseruse-g4: yes. Head logs show a variable-not-associated error that the re-indented request block causes when the schema flag is false, in cases from both change and diff sources.
- deepagents-g2: no. The only broken case (d-g2-posttool-hook-shell, from the diff) runs one shell call with PostToolUse and Stop hooks and no subagents, so it does not show the parallel task channel conflict. It may relate to the second hook-resume fix, but nothing readable confirms that.
- deepagents-g4: yes. Eight broken cases carry KeyError e, the stated unescaped placeholder error.
- gptr-g2: yes. All 15 cases crash on the research run, and the diff uses typing names before importing them. The traceback is cut off before the exception name.
- odr-g2: yes. The change cases g2-chg-clarify-node and g2-chg-clear-with-clarify-on show the exact AttributeError.
- pydanticai-g4: yes. The diff case with the server already running fails on the sampled model and hits the request limit. No transcript is stored, so the mechanism is inferred.
- strands-g2: yes. Both async session-resume change cases show asyncio.run inside a running event loop.

Totals: 7 yes, 0 partly, 1 no.

Controls: steps (a), (b) and (c)

- odr-g1: a no, b yes (weak), c no. Label: false block. The later upstream commits only fix get_today_str, which has nothing to do with the broken search and facts checks.
- deepagents-g1: a no, b yes, c no. Label: false block. The later effort commits concern the interactive effort picker and cache warnings, not the headless model-params path.

## Correction after the reproduction rerun (2026-11-23 15:10Z)

The step (a) rerun for odr-g1 that this adjudication read was invalid: the rerun could not import
the project adapter, so every run crashed and the "does not reproduce" result came from missing
files (see DEV_NOTES.md). The corrected rerun (`confirm.py`, evidence/odr-g1/confirm.json)
reproduces the block, and base against base passes. odr-g1 is therefore a yes, b yes (weak),
c no: two of three, labelled **unconfirmed**, which under the rule still counts as a false block.
deepagents-g1 does not reproduce on the corrected rerun either and stays a false block.
