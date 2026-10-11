from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
cases = json.loads((root / 'data' / 'synthetic_cases.json').read_text())
for case in cases:
    path = root / 'data' / 'synthetic_cases' / f"{case['case_id']}.json"
    path.write_text(json.dumps(case, indent=2))
print(f'Wrote {len(cases)} synthetic cases.')
