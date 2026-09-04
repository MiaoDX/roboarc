"""Reachy-specific API process wired to the SDK-facing simulator endpoint."""

import os

from roboarc.api import create_app

from .adapter import ReachyAdapter, connect_reachy

app = create_app(ReachyAdapter(connect_reachy(os.environ.get("REACHY_HOST", "127.0.0.1"))))
