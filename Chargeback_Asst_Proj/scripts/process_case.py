from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.schemas.case import DisputeCase
from app.services.case_service import CaseService


def main():
    parser = argparse.ArgumentParser(description='Process a synthetic case file.')
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.case).read_text())
    case = DisputeCase(**payload)
    result = CaseService().process_case(case)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
