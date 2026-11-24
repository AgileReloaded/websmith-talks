#!/usr/bin/env python3
"""Install the same release format locally, without downloading or overwriting."""
import argparse
import json
from pathlib import Path
import sys

from build_release import ROOT, package
from manage import install


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        raw, sha = package((ROOT / "VERSION").read_text().strip())
        result = install(args.project_root, raw, sha)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"installed": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
