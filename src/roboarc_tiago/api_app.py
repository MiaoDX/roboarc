"""Explicit API entry point for the TIAGo ROS/Gazebo lane."""

from roboarc.api.app import create_app

from .adapter import TiagoRosAdapter

app = create_app(TiagoRosAdapter())
