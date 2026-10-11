"""Writes the API's OpenAPI schema to a file, so the web can generate its types.

Usage: python -m app.export_openapi <path>
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = Path(sys.argv[1])
    path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
