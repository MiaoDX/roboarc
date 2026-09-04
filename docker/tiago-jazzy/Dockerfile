FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        python3-pip \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-venv \
        python3-vcstool \
        ros-jazzy-control-msgs \
        ros-jazzy-gz-ros2-control \
        ros-jazzy-nav2-msgs \
        ros-jazzy-ros-gz \
        ros-jazzy-tf2-ros \
    && rm -rf /var/lib/apt/lists/*

COPY docker/tiago-jazzy/tiago.repos /tmp/tiago.repos
COPY docker/tiago-jazzy/patches /overlay-patches
COPY docker/tiago-jazzy/apply-overlay-patches.sh /usr/local/bin/apply-overlay-patches
RUN mkdir -p /tiago_ws/src \
    && vcs import --input /tmp/tiago.repos /tiago_ws/src \
    && /usr/local/bin/apply-overlay-patches /tiago_ws /overlay-patches \
    && apt-get update \
    && rosdep install --from-paths /tiago_ws/src -y --ignore-src --rosdistro jazzy \
        --skip-keys="gazebo_ros gazebo_plugins gazebo_ros2_control gazebo_planar_move_plugin gz-sensors6 pal_gazebo_plugins" \
    && cd /tiago_ws \
    && . /opt/ros/jazzy/setup.sh \
    && colcon build --merge-install \
    && rm -rf /tiago_ws/build /tiago_ws/log /var/lib/apt/lists/* /tmp/tiago.repos

WORKDIR /workspace
COPY . .
RUN python3 -m venv --system-site-packages /opt/roboarc-venv \
    && /opt/roboarc-venv/bin/python -m pip install --upgrade pip \
    && /opt/roboarc-venv/bin/pip install -e ".[dev,rerun]"

ENV PATH="/opt/roboarc-venv/bin:$PATH"
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

COPY docker/tiago-jazzy/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
