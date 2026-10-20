"""Run every gold query on Chinook and write the Flywheel dataset with the values to expect."""

import json
import sqlite3
import sys

from questions import Q

from flywheel.dataset import inputs_id

db = sqlite3.connect(sys.argv[1])
out = open(sys.argv[2] if len(sys.argv) > 2 else "dataset.jsonl", "w")  # noqa: SIM115
for level, question, sql, _ in Q:
    rows = db.execute(sql).fetchall()
    assert len(rows) == 1, (question, rows)
    values = [str(v) for v in rows[0]]
    inputs = {"question": question}
    out.write(
        json.dumps(
            {
                "id": inputs_id(inputs),
                "inputs": inputs,
                "reference_outputs": {"must_include": values, "gold_sql": sql},
                "metadata": {"source": "hand-written", "level": level},
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(level, values)
