#!/usr/bin/env python3
"""Pick harmless control commits for each frozen regression, reproducibly (seed 20261122).

For every regression in REGRESSIONS this lists the candidate commits that satisfy the study's
control rules, shuffles them with a generator seeded 20261122 (fresh per regression), and walks the shuffled list taking the
first two whose parent installed (per /tmp/rr/install_log.jsonl, written by the install check).

Candidate rules (PLAN.md "Harmless controls" and the freeze brief):
  * non-merge commit reachable from the default branch (main), committer date within 45 days
    either side of the introducing commit's committer date;
  * touches at least one non-test file under the same top-level package directory the
    introducing commit touched (PKG below), with a Python or prompt-like extension;
  * not dependency/CI/docs-only (subject prefix filter plus a file filter);
  * not itself a revert, not a commit named in the survey (intro or fix of any pair);
  * no later commit on main reverts it or describes it as a fix/regression target: a later
    message containing its sha (7+ hex prefix), `Revert "<its subject>"`, or its PR number
    (#N from its subject) together with revert/regress/broke/broken/fix.

Usage:
  python3 pick_controls.py --list      # print shuffled candidate order per regression (no install data needed)
  python3 pick_controls.py --pick      # choose 2 per regression using /tmp/rr/install_log.jsonl
Writes /tmp/rr/controls_pick.json with the full ordered lists and the choices.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import subprocess
from functools import lru_cache

SEED = 20261122
WINDOW_DAYS = 45
OSS = '/tmp/oss'
OUT = '/tmp/rr/controls_pick.json'  # working output; the frozen choices are copied into cases.json

# id, repo clone dir, introducing sha, top-level package dir the intro touched
REGRESSIONS = [
    ('adk-tool-round-cap', 'google_adk-python', 'd185ca5ac50f493cdcb9552d2ab4e9d1e30a1b34', 'src/google/adk/'),
    ('adk-clone-subagent-tools', 'google_adk-python', 'b41fc578a5db964701fce5cab0f9d26c5d6eaaf0', 'src/google/adk/'),
    ('adk-a2a-hitl-confirm', 'google_adk-python', '9e9eaa69bdcc16f004af9c63f40f1dae6404c29b', 'src/google/adk/'),
    ('adk-workflow-rerun-on-resume', 'google_adk-python', 'bcac35a6efb21f176eef9d28d663db247f4e5afd', 'src/google/adk/'),
    ('adk-instruction-nested-state', 'google_adk-python', '94c43a269dcf6691556d38aef46360f04f736584', 'src/google/adk/'),
    ('adk-openapi-httpx', 'google_adk-python', '9290b966267dc02569786f95aab2a3cb78c7004f', 'src/google/adk/'),
    ('agno-mcp-init-headers', 'agno-agi_agno', '7a4e21b08237df83d0a9b771143a14b21adea592', 'libs/agno/agno/'),
    ('bu-loop-empty-result-repair', 'browser-use_browser-use', 'da52db9dffa7f2670e992bc878b6cae6aaad87fb', 'browser_use/'),
    ('bu-browsererror-reraise', 'browser-use_browser-use', 'f30c3952c9a206954687196838bd38b913910404', 'browser_use/'),
    ('bu-openai-structured-indent', 'browser-use_browser-use', '62d19f0c9a18e38978888c5416458f760c6393c6', 'browser_use/'),
    ('deepagents-code-server-hooks', 'langchain-ai_deepagents', '2487c4b87dff264ae1e8d34c7ce9249dd4b29760', 'libs/code/deepagents_code/'),
    ('deepagents-sandbox-heredoc-format', 'langchain-ai_deepagents', 'f21ee57df3f9946b1c9b2a0351496692f23e48d7', 'libs/deepagents/deepagents/'),
    ('deepagents-sandbox-crlf-edit', 'langchain-ai_deepagents', '6c2d559b574a5a5d9de3adc36d6cf02d6cf93d9d', 'libs/deepagents/deepagents/'),
    ('smolagents-planning-memory', 'huggingface_smolagents', '7a128dbf8e14d242786c5df927cd7f5e8e83cc41', 'src/smolagents/'),
    ('smolagents-exec-timeout', 'huggingface_smolagents', '6b4ad144cd262f99dc8ef1d48ec1d694d16b0966', 'src/smolagents/'),
    ('miniswe-toolcall-error-template', 'SWE-agent_mini-swe-agent', '640165a535e6b6bcdc68f99fc447fb31154206d6', 'src/minisweagent/'),
    ('crewai-repeated-call-guard', 'crewAIInc_crewAI', 'c069653b83518331ecac778a661cfe5cb91c4dd3', 'lib/crewai/src/crewai/'),
    ('autogen-reflection-system-msg', 'microsoft_autogen', 'a02d08a8efb4ddd925e9a32e3ce3df3643938a63', 'python/packages/autogen-agentchat/'),
    ('pydanticai-history-user-first', 'pydantic_pydantic-ai', '468e60a5cf73ea38aeab912d87b7ff7522f6bb80', 'pydantic_ai_slim/pydantic_ai/'),
    ('pydanticai-mcp-sampling-contextvar', 'pydantic_pydantic-ai', '49658f3e5fa701c8d6470872a097ae81d02ccf77', 'pydantic_ai_slim/pydantic_ai/'),
    ('gptr-query-processing-import', 'assafelovic_gpt-researcher', 'bcc1eac0ca56eb2509f2b6384b6d7117eb1fce87', 'gpt_researcher/'),
    ('strands-session-concurrent-read', 'strands-agents_sdk-python', '08dc4aeaad6e75dc273d41a9898e0d08df09863b', 'src/strands/'),
    ('odr-get-today-str', 'open_deep_research', '0c9b239cb63e9ed3cb4c1e346d374596f3d6a6ff', 'src/open_deep_research/'),
    ('oh-view-command-prompt', 'All-Hands-AI_OpenHands', 'f0dbb02ee146eec0e2d63bf313302a53809023c6', 'openhands/'),
    ('oh-max-output-tokens', 'All-Hands-AI_OpenHands', '1e33624951bdddbfc23cd17324d2367bf94ed002', 'openhands/'),
    ('oh-completion-message-list', 'All-Hands-AI_OpenHands', 'e68abf8d754078d6593ede7df38098787c8f0b1d', 'openhands/'),
    ('oh-httphandler-fd-leak', 'All-Hands-AI_OpenHands', 'a20f29957939f7c3d4ac6d03ade11790a5706235', 'openhands/'),
    ('oh-initial-msg-after-condense', 'All-Hands-AI_OpenHands', '4b1ed30e97f22e7c4907a249902b0a9bda4b612d', 'openhands/'),
    ('oh-condensation-loop-3', 'All-Hands-AI_OpenHands', '22064d5555f355c270f9ab2a85ae57fb7e02495b', 'openhands/'),
]

PROMPT_EXT = ('.py', '.j2', '.jinja', '.jinja2', '.md', '.txt', '.yaml', '.yml', '.prompt')
SKIP_SUBJECT = re.compile(
    r'^(revert\b|docs?[(:!\s]|ci[(:!\s]|build[(:!\s]|test[s]?[(:!\s]|style[(:!\s]|chore\((deps|release|ci|docs)\)|'
    r'release[(:!\s]|bump\b|\[pre-commit|pre-commit)|bump version|dependabot|update (uv|poetry)\.lock',
    re.I)
NON_CODE = re.compile(r'(^|/)(tests?|docs?|examples?|cookbook|\.github|evaluation)(/|$)|(^|/)test_[^/]*$|_test\.py$|'
                      r'(uv|poetry)\.lock$|requirements[^/]*\.txt$|pyproject\.toml$|package(-lock)?\.json$')
FIXWORD = re.compile(r'revert|regress|broke|broken|\bfix', re.I)


def git(d: str, *args: str) -> str:
    return subprocess.run(['git', '-c', 'gc.auto=0', '-C', f'{OSS}/{d}', *args],
                          capture_output=True, text=True, check=True).stdout


@lru_cache(maxsize=None)
def history(d: str) -> list[tuple[str, int, int, str, str]]:
    """(sha, committer time, parent count, subject, body) for every commit reachable from main."""
    out = git(d, 'log', 'main', '--format=%H%x1f%ct%x1f%P%x1f%s%x1f%B%x1e')
    rows = []
    for rec in out.split('\x1e'):
        rec = rec.strip('\n')
        if not rec:
            continue
        sha, ct, parents, subj, body = rec.split('\x1f', 4)
        rows.append((sha, int(ct), len(parents.split()), subj, body))
    return rows


@lru_cache(maxsize=None)
def survey_shas(d: str) -> frozenset[str]:
    """Full shas of every intro/fix commit the survey named for this repo."""
    out = set()
    for f in glob.glob('/tmp/oss/out/*.jsonl'):
        for line in open(f):
            r = json.loads(line)
            if r['repo'].replace('/', '_') != d:
                continue
            for k in ('intro_sha', 'fix_sha'):
                if r.get(k):
                    try:
                        out.add(git(d, 'rev-parse', r[k]).strip())
                    except subprocess.CalledProcessError:
                        pass
    return frozenset(out)


def files(d: str, sha: str) -> list[str]:
    return [p for p in git(d, 'diff-tree', '--no-commit-id', '--name-only', '-r', sha).splitlines() if p]


@lru_cache(maxsize=None)
def blame_index(d: str):
    """Indexes over every commit message on main: hex tokens, reverted subjects, PR refs with a fix word."""
    hexes: dict[str, list[tuple[int, str]]] = {}
    reverted: dict[str, list[tuple[int, str]]] = {}
    prs: dict[str, list[tuple[int, str]]] = {}
    for osha, oct_, _np, _osubj, obody in history(d):
        for tok in set(re.findall(r'\b[0-9a-f]{7,40}\b', obody)):
            hexes.setdefault(tok[:7], []).append((oct_, osha))
        for s in re.findall(r'Revert "(.+?)"', obody):
            reverted.setdefault(s, []).append((oct_, osha))
        if FIXWORD.search(obody):
            for n in set(re.findall(r'#(\d+)\b', obody)):
                prs.setdefault(n, []).append((oct_, osha))
    return hexes, reverted, prs


def later_blames(d: str, sha: str, ct: int, subj: str) -> str | None:
    """Return the first later commit that reverts or fixes this one, else None.

    Later = committer time at or after this commit's, excluding itself. A hit is a message that
    names this commit's sha (7+ hex prefix), says Revert "<this subject>", or names this commit's
    PR number (#N at the end of its subject) together with revert/regress/broke/broken/fix.
    """
    hexes, reverted, prs = blame_index(d)
    pr = re.findall(r'\(#(\d+)\)\s*$', subj)
    hits = list(hexes.get(sha[:7], [])) + list(reverted.get(subj, []))
    if pr:
        hits += prs.get(pr[0], [])
    for oct_, osha in sorted(hits):
        if oct_ >= ct and osha != sha:
            return osha
    return None


def candidates(rid: str, d: str, intro: str, pkg: str) -> list[str]:
    rows = {r[0]: r for r in history(d)}
    ict = rows[intro][1]
    lo, hi = ict - WINDOW_DAYS * 86400, ict + WINDOW_DAYS * 86400
    excluded = survey_shas(d) | {intro}
    out = []
    for sha, ct, np_, subj, _body in history(d):
        if not (lo <= ct <= hi) or np_ != 1 or sha in excluded:
            continue
        if SKIP_SUBJECT.search(subj):
            continue
        fs = files(d, sha)
        code = [p for p in fs if p.startswith(pkg) and p.endswith(PROMPT_EXT) and not NON_CODE.search(p)]
        if not code:
            continue
        if later_blames(d, sha, ct, subj):
            continue
        out.append(sha)
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--pick', action='store_true')
    ap.add_argument('--installed', default='/tmp/rr/install_log.jsonl')
    a = ap.parse_args()
    installed: dict[str, bool] = {}
    if a.pick and os.path.exists(a.installed):
        for line in open(a.installed):
            r = json.loads(line)
            installed[r['sha']] = r['ok']  # later lines win
    result = {'seed': SEED, 'window_days': WINDOW_DAYS, 'regressions': []}
    taken: set[str] = set()
    for rid, d, intro, pkg in REGRESSIONS:
        cands = candidates(rid, d, intro, pkg)
        order = cands[:]  # sorted by sha
        random.Random(SEED).shuffle(order)  # fresh generator per regression: editing the list never moves another's picks
        chosen, skipped, unchecked = [], [], []
        for sha in order:
            if len(chosen) == 2:
                break
            if sha in taken:
                skipped.append({'sha': sha, 'why': 'already a control for another regression'})
                continue
            parent = git(d, 'rev-parse', sha + '^').strip()
            if a.pick:
                if parent not in installed:
                    unchecked.append(sha)
                    break  # stop: the next one in order must be checked before choosing further
                if not installed[parent]:
                    skipped.append({'sha': sha, 'why': 'parent did not install'})
                    continue
            chosen.append(sha)
            taken.add(sha)
        result['regressions'].append({'id': rid, 'repo_dir': d, 'intro_sha': intro, 'pkg_dir': pkg,
                                      'n_candidates': len(cands), 'shuffled_order': order,
                                      'chosen': chosen, 'skipped': skipped, 'needs_install_check': unchecked})
        print(f'{rid}: {len(cands)} candidates; chosen {[c[:10] for c in chosen]}'
              + (f'; check install of parent of {unchecked[0][:10]}' if unchecked else ''))
    with open(OUT, 'w') as f:
        json.dump(result, f, indent=1)


if __name__ == '__main__':
    main()
