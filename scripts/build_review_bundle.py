#!/usr/bin/env python3
"""Build a self-contained static Review site from generated and recorded artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_local_review import generate
from scripts.serve_review_artifacts import discover_reviews
from scripts.validate_review_artifacts import ReviewArtifactError, validate_review_artifacts


def _copy_review_artifact(source: Path, target_root: Path) -> None:
    try:
        manifest = json.loads((source / "review.json").read_text(encoding="utf-8"))
        validate_review_artifacts(source)
    except (OSError, json.JSONDecodeError, ReviewArtifactError) as error:
        raise RuntimeError(f"invalid review artifact {source}: {error}") from error

    target = target_root / source.name
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "review.json", target / "review.json")
    artifacts = manifest["artifacts"]
    names = {artifacts["trace"], artifacts["video"]}
    if artifacts.get("rerun") is not None:
        names.add(artifacts["rerun"])
    timeline = manifest.get("timeline")
    if isinstance(timeline, dict):
        for media in timeline.get("media", []):
            if isinstance(media, dict) and isinstance(media.get("artifact"), str):
                names.add(media["artifact"])
    for name in names:
        shutil.copy2(source / name, target / name)


async def build(args: argparse.Namespace) -> Path:
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to replace existing output directory: {output}")
    output.mkdir(parents=True)
    shutil.copytree(args.web_dist, output, dirs_exist_ok=True)
    index_path = output / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    if 'src="/' in index_html or 'href="/' in index_html:
        raise RuntimeError(
            "web dist must use relative asset paths; build with ROBOARC_REVIEW_BASE=./"
        )
    marker = '<meta name="roboarc-default-view" content="review">'
    if "<head>" in index_html:
        index_html = index_html.replace("<head>", f"<head>{marker}", 1)
    else:
        index_html = f"{marker}\n{index_html}"
    index_path.write_text(index_html, encoding="utf-8")
    artifact_root = output / "artifacts"
    artifact_root.mkdir()

    await generate(args.workflows / "mock-demo.json", artifact_root, "mock")
    await generate(args.workflows / "simulation-observable.json", artifact_root, "simulation")

    for source in sorted(args.recorded_artifacts.iterdir()):
        if not source.is_dir() or not (source / "review.json").is_file():
            continue
        if source.name in {"mock-demo", "simulation-observable"}:
            continue
        _copy_review_artifact(source, artifact_root)

    reviews = discover_reviews(artifact_root)
    required_ids = {
        "mock-demo",
        "simulation-observable",
        "tiago-look-and-say",
        "tiago-observable",
        "tiago-proof-final",
        "reachy-proof-final",
    }
    review_ids = {str(review["id"]) for review in reviews}
    missing_ids = sorted(required_ids - review_ids)
    if missing_ids:
        raise RuntimeError(f"review bundle is missing required demos: {missing_ids}")
    (artifact_root / "reviews.json").write_text(
        json.dumps(reviews, indent=2), encoding="utf-8"
    )
    (output / "REVIEW.md").write_text(
        "# RoboArc Review\n\n"
        "Open `/` or `/?review` in a browser. To view this bundle locally:\n\n"
        "```bash\npython -m http.server 8000 --directory .\n```\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-dist", type=Path, required=True)
    parser.add_argument("--recorded-artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--workflows", type=Path, default=Path("examples/workflows"))
    parser.add_argument("--output", type=Path, default=Path("review-site"))
    args = parser.parse_args()
    asyncio.run(build(args))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
