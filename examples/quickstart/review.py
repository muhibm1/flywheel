"""Stands in for the person who reviews mined candidates.

`flywheel mine` proposes each failing trace as a case with no reference answer, because only a
person knows what the agent should have done. In a real project they write it in the candidates
file or in a LangSmith annotation queue. For the quickstart this script writes the answer a
reviewer would give: a customer asking for their money back belongs with billing.

    python review.py .flywheel/candidates.jsonl
"""

import json
import sys
from pathlib import Path


def main(path: str) -> None:
    """Fill in the reference team for every candidate that asks for money back."""
    file = Path(path)
    reviewed = []
    for line in file.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if "money back" in case["inputs"]["message"].lower():
            case["reference_outputs"] = {"team": "billing"}
        reviewed.append(json.dumps(case, sort_keys=True))
    file.write_text("\n".join(reviewed) + "\n", encoding="utf-8")
    print(f"Reviewed {len(reviewed)} candidate(s) in {file}")


if __name__ == "__main__":
    main(sys.argv[1])
