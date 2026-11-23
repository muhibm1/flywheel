"""Build the blind workspaces the case writers see, and the sealed key they never see.

Each gate (a regression, or its first seeded control) gets a neutral id like `crewai-g3`, shuffled
with a fixed seed, so neither the id nor the order tells a writer which gates are regressions. A
workspace holds only what a reviewer sees when a pull request opens: the source tree at the base
commit, the change's diff, and its title and message. The key mapping ids to cases stays in the
sealed folder.
"""
import json, random, subprocess, sys
from pathlib import Path

SEALED = Path(sys.argv[1]); BLIND = Path(sys.argv[2]); OSS = Path(sys.argv[3])
cases = json.loads((SEALED / "cases.json").read_text())
REPO_DIR = {"google/adk-python": "google_adk-python", "agno-agi/agno": "agno-agi_agno",
            "browser-use/browser-use": "browser-use_browser-use", "langchain-ai/deepagents": "langchain-ai_deepagents",
            "huggingface/smolagents": "huggingface_smolagents", "SWE-agent/mini-swe-agent": "SWE-agent_mini-swe-agent",
            "crewAIInc/crewAI": "crewAIInc_crewAI", "microsoft/autogen": "microsoft_autogen",
            "pydantic/pydantic-ai": "pydantic_pydantic-ai", "assafelovic/gpt-researcher": "assafelovic_gpt-researcher",
            "strands-agents/sdk-python": "strands-agents_sdk-python", "langchain-ai/open_deep_research": "open_deep_research",
            "All-Hands-AI/OpenHands": "All-Hands-AI_OpenHands"}
SHORT = {"google/adk-python": "adk", "agno-agi/agno": "agno", "browser-use/browser-use": "browseruse",
         "langchain-ai/deepagents": "deepagents", "huggingface/smolagents": "smolagents",
         "SWE-agent/mini-swe-agent": "miniswe", "crewAIInc/crewAI": "crewai", "microsoft/autogen": "autogen",
         "pydantic/pydantic-ai": "pydanticai", "assafelovic/gpt-researcher": "gptr",
         "strands-agents/sdk-python": "strands", "langchain-ai/open_deep_research": "odr",
         "All-Hands-AI/OpenHands": "openhands"}
gates = [c for c in cases if c["kind"] == "regression" or c["id"].endswith("--control1")]
rng = random.Random(20261122)
by_repo = {}
for g in gates:
    by_repo.setdefault(g["repo"], []).append(g)
key = {}
for repo, gs in sorted(by_repo.items()):
    rng.shuffle(gs)
    for i, g in enumerate(gs, 1):
        gid = f"{SHORT[repo]}-g{i}"
        key[gid] = g["id"]
        d = BLIND / SHORT[repo] / gid
        d.mkdir(parents=True, exist_ok=True)
        clone = OSS / REPO_DIR[repo]
        diff = subprocess.run(["git", "-C", str(clone), "diff", g["base_sha"], g["head_sha"]], capture_output=True, text=True, check=True).stdout
        msg = subprocess.run(["git", "-C", str(clone), "log", "-1", "--format=%s%n%n%b", g["head_sha"]], capture_output=True, text=True, check=True).stdout
        (d / "change.diff").write_text(diff)
        (d / "change-message.txt").write_text(msg)
        src = Path("/tmp/rr/src") / f"{SHORT[repo] if SHORT[repo] not in ('browseruse','miniswe','pydanticai','gptr','openhands','odr') else ''}"
        (d / "gate.json").write_text(json.dumps({"gate": gid, "repo": repo, "base_sha": g["base_sha"], "head_sha": g["head_sha"]}, indent=1))
(SEALED / "gate-key.json").write_text(json.dumps(key, indent=1))
print(len(key), "gates")
