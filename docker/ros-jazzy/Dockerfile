FROM ros:jazzy-ros-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip python3-venv python3-yaml ros-jazzy-example-interfaces && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY . .
RUN python3 -m venv --system-site-packages /opt/roboarc-venv && /opt/roboarc-venv/bin/python -m pip install --upgrade pip && /opt/roboarc-venv/bin/pip install -e ".[dev]"
ENV PATH="/opt/roboarc-venv/bin:$PATH"
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
CMD ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && python -m pytest -p pytest_asyncio.plugin tests/ros"]
