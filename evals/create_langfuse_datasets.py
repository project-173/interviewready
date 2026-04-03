"""Create the Langfuse datasets defined in evals/datasets-new."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(BACKEND_DIR / ".env")
except Exception as exc:
    print(f"Warning: failed to load .env files: {exc}")

from langfuse import Langfuse

from app.core.config import settings
from evals.langfuse_datasets import load_dataset_specs, sync_langfuse_datasets


def _parse_datasets(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    items = {item.strip() for item in raw.split(",") if item.strip()}
    return items or None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Langfuse datasets from evals/datasets-new"
    )
    parser.add_argument(
        "--datasets",
        help="Comma-separated dataset names to create (default: all)",
    )
    args = parser.parse_args()

    if not settings.LANGFUSE_PUBLIC_KEY:
        print("Error: LANGFUSE_PUBLIC_KEY is not set.")
        return

    specs = load_dataset_specs()
    selected = _parse_datasets(args.datasets)
    if selected:
        specs = {name: spec for name, spec in specs.items() if name in selected}
        missing = sorted(selected - set(specs.keys()))
        if missing:
            print("Unknown dataset names: " + ", ".join(missing))
            return

    langfuse = Langfuse()
    sync_langfuse_datasets(langfuse=langfuse, specs=specs.values())

    try:
        langfuse.flush()
        print("Langfuse flush complete")
    except Exception as exc:
        print(f"Langfuse flush failed: {exc}")


if __name__ == "__main__":
    main()
