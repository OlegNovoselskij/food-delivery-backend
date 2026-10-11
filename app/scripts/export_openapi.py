import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OpenAPI schema written to {target}")


if __name__ == "__main__":
    main()
