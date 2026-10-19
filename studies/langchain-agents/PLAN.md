# Plan, written before the results (2026-10-19)

This study runs Flywheel on two agents LangChain publishes as open source. The plan below was
fixed before any score was seen, so the cases and the changes could not be picked to flatter
Flywheel. Whatever comes out is reported.

## The agents

| Agent | Where it comes from | What it does |
|---|---|---|
| Email assistant | `langchain-ai/agents-from-scratch`, `src/email_assistant/email_assistant.py` | Sorts an email into ignore, notify or respond, then drafts the reply and books meetings with tools. |
| Text-to-SQL Deep Agent | `langchain-ai/deepagents`, `examples/text-to-sql-agent` | Answers questions about a music store's database (Chinook) by exploring tables and writing SQL, built on LangChain's Deep Agents framework. |

Both run unchanged except for the model object. The email assistant ships on OpenAI's gpt-4.1;
here it runs on Claude. The SQL agent ships on Claude Sonnet 4.5, which is what it runs on here.

## The cases

- **Email, LangChain's own 16.** The labelled emails in the repository's
  `eval/email_dataset.py`, with LangChain's labels, expected tool calls and reply criteria,
  scored by LangChain's own three checks (right category, expected tools called, a model judge
  on the criteria).
- **Email, 29 traffic emails.** New, realistic emails to the same inbox, labelled from the
  agent's own written triage rules before any run, each citing the rule that decides it. They
  go through the agent once each, like a day of mail. The ones it gets wrong are mined into
  test cases, which is Flywheel's first step.
- **SQL, 24 questions.** Six easy, eight medium, ten hard, each with a gold SQL query written by
  hand. The expected values come from running the gold query on the database, never typed in.
  Checks are code only: the answer contains every expected value, and every query run was a
  read.

## The changes Flywheel gates

The change is the one a customer asks an FDE about most: **can we move this agent to the
cheaper model?** For both agents, main runs on Claude Sonnet 4.5 and the change moves every
model call to Claude Haiku 4.5, about a third of the price per token.

Each gate is paired with a **control**: main against a second, independent run of main. A
control that passes shows a red check means a real change, not model noise.

Every experiment runs each case 3 times. Flywheel's decision rules are its defaults: a case is
broken when its pass rate falls by at least half (two of three runs flipping), and one broken
case blocks.

## Where the runs happen

Everything runs on the Claude subscription through headless Claude Code, at no API cost. A
small paid run on the Anthropic API then repeats the cheaper-model side with LangChain's native
`ChatAnthropic` client, to check that the subscription route gives the same verdicts. Its cost
is stated, and approved, before it runs.
