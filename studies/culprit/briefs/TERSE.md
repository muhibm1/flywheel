# Terse reporter brief: rewrite a bug report the way a hurried end user would file it

Your case folder has `REPORT.md`, a careful bug report. Rewrite it as the short note a busy user
would actually send. Read nothing else. Run nothing.

Rules for the rewrite:

- A title of at most ten words and a body of at most three sentences. Plain prose only.
- Say what the user was trying to do and what went wrong, in product terms.
- No code, no snippets, no file paths, no configuration keys.
- No names of classes, functions, methods, parameters, modules or exception types. Name the
  product and the feature the way its documentation front page would ("the server", "the proxy
  setting", "loop detection"), nothing more internal than that.
- No exact error text. You may say that an error appeared and give its gist in your own words.
- No numbers that are not needed to understand the symptom.
- End with one sentence saying it worked before upgrading.
- Do not guess at a cause.

Write the result to `terse.txt` in the case folder with the Write tool. Final message: `done`, or
if the write is refused, the full text of the rewrite and nothing else.
