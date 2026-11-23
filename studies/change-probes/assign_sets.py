"""Split audited regressions and their controls into sets, by project, and give every change a neutral id.

usage: assign_sets.py <sealed folder> [--h1 60] [--d2 20] [--cap 8]

Whole projects go to one set, so nothing learnt on a practice project can help on a held-out one.
Projects are taken in a fixed shuffled order (the seed is in this file, chosen before any row was
seen by the gate): the held-out set H1 is filled first, then the practice set D2, and what is left
is the spare held-out set H2. A project contributes at most `cap` regressions.

Writes, in the sealed folder:
  sets/key.json          every change with its set, kind and full answer row (never shown to a gate)
  sets/<SET>.public.json what a gate builder may see: id, repo, base, head, install details only
Prints counts only.
"""
import hashlib
import json
import random
import sys
from pathlib import Path

SEED = "change-probes-2026-11-23-sets-v1"


def arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def python_only(row):
    tests = (row.get("witness") or {}).get("tests") or []
    return bool(tests) and all(".py" in t for t in tests)


def main():
    sealed = Path(sys.argv[1])
    n_h1, n_d2, cap = arg("--h1", 60), arg("--d2", 20), arg("--cap", 8)
    projects = {}
    for f in sorted((sealed / "audited").glob("*.json")):
        rows = [r for r in json.loads(f.read_text())
                if r.get("kept") and r.get("audit") and python_only(r)
                and str(r.get("intro_date", ""))[:10] >= "2026-07-01"
                and int(r.get("changed_source_lines") or 0) <= 2000]
        seen, uniq = set(), []
        for r in rows:
            if r["intro_sha"] not in seen:
                seen.add(r["intro_sha"])
                uniq.append(r)
        if uniq:
            projects[f.stem] = uniq
    order = sorted(projects, key=lambda p: hashlib.sha256((SEED + p).encode()).hexdigest())
    sets = {"H1": [], "D2": [], "H2": []}
    counts = {"H1": 0, "D2": 0, "H2": 0}
    want = {"H1": n_h1, "D2": n_d2, "H2": 10**9}
    for p in order:
        rows = projects[p][:cap]
        for s in ("H1", "D2", "H2"):
            if counts[s] < want[s]:
                take = rows[: want[s] - counts[s]]
                sets[s].append((p, take))
                counts[s] += len(take)
                break
    rng = random.Random(SEED)
    key, out_dir = [], sealed / "sets"
    out_dir.mkdir(parents=True, exist_ok=True)
    for s, plist in sets.items():
        items = []
        for p, rows in plist:
            cf = sealed / "controls" / f"{p}.json"
            controls = {c["paired_intro_sha"]: c for c in json.loads(cf.read_text())} if cf.exists() else {}
            for r in rows:
                items.append({"kind": "regression", "project": p, "repo": r["repo"],
                              "base_sha": r["base_sha"], "head_sha": r["intro_sha"],
                              "python": r.get("python"), "install": r.get("install"),
                              "source_root": r.get("source_root"), "row": r})
                c = controls.get(r["intro_sha"])
                if c:
                    items.append({"kind": "control", "project": p, "repo": c["repo"],
                                  "base_sha": c["base_sha"], "head_sha": c["head_sha"],
                                  "python": c.get("python"), "install": c.get("install"),
                                  "source_root": c.get("source_root"), "row": c})
        rng.shuffle(items)
        public = []
        for i, it in enumerate(items, 1):
            it["set"], it["gate_id"] = s, f"{s.lower()}-{i:03d}"
            key.append(it)
            public.append({k: it[k] for k in ("gate_id", "repo", "project", "base_sha", "head_sha",
                                               "python", "install", "source_root")})
        (out_dir / f"{s}.public.json").write_text(json.dumps(public, indent=1))
        print(s, "projects", len(plist), "regressions", sum(1 for i in items if i["kind"] == "regression"),
              "controls", sum(1 for i in items if i["kind"] == "control"))
    (out_dir / "key.json").write_text(json.dumps(key, indent=1))


if __name__ == "__main__":
    main()
