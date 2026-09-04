#!/usr/bin/env python3
"""Serve review artifacts and a catalog discovered from valid manifests."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from scripts.validate_review_artifacts import ReviewArtifactError, validate_review_artifacts


def discover_reviews(root: Path, workflows_root: Path | None = None) -> list[dict[str, object]]:
    candidates = [root] if (root / "review.json").is_file() else sorted(
        path for path in root.iterdir() if path.is_dir() and (path / "review.json").is_file()
    )
    reviews_by_workflow: dict[str, dict[str, object]] = {}
    for directory in candidates:
        try:
            validate_review_artifacts(directory)
        except ReviewArtifactError as error:
            print(f"skipping invalid review {directory}: {error}")
            continue
        manifest = json.loads((directory / "review.json").read_text(encoding="utf-8"))
        workflow = manifest["workflow"]
        reviews_by_workflow[workflow["id"]] = {
            "id": directory.name,
            "artifact_root": "" if directory == root else directory.name,
            "manifest": manifest,
            "workflow": workflow,
            "profile_id": manifest.get("profile_id") or workflow.get("profile_id"),
            "recorded": True,
        }
    if workflows_root is not None and workflows_root.is_dir():
        for path in sorted(workflows_root.glob("*.json")):
            workflow = json.loads(path.read_text(encoding="utf-8"))
            workflow_id = workflow.get("id")
            if not isinstance(workflow_id, str):
                continue
            reviews_by_workflow.setdefault(
                workflow_id,
                {
                    "id": workflow_id,
                    "artifact_root": "",
                    "manifest": None,
                    "workflow": workflow,
                    "profile_id": workflow.get("profile_id"),
                    "recorded": False,
                },
            )
    return sorted(reviews_by_workflow.values(), key=lambda item: str(item["workflow"]["name"]))


def handler_for(root: Path, reviews: list[dict[str, object]]):
    class ReviewHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def do_GET(self) -> None:
            if urlsplit(self.path).path == "/reviews.json":
                body = json.dumps(reviews).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    return ReviewHandler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--workflows", type=Path, default=None)
    args = parser.parse_args()
    root = args.directory.resolve()
    reviews = discover_reviews(root, args.workflows.resolve() if args.workflows else None)
    if not reviews:
        parser.error(f"no valid review artifacts found below {root}")
    print(f"Serving a catalog of {len(reviews)} demo(s) from {root}", flush=True)
    ThreadingHTTPServer((args.bind, args.port), handler_for(root, reviews)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
