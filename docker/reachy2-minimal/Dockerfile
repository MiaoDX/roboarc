FROM python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534 AS runtime

ARG REACHY2_MUJOCO_COMMIT=f6d8284e812d3b96b557e2e844d55bd09d6e3ee6
ARG REACHY2_SYMBOLIC_IK_COMMIT=31e6a2375f83d09e19af16dadb7f70bb96fbbd65

ENV DEBIAN_FRONTEND=noninteractive \
    MUJOCO_GL=egl \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libegl1 \
        libgl1 \
        libglfw3 \
        libx11-6 \
        libxext6 \
        libxrender1 \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
        "numpy<2" \
        "mujoco==3.2.6" \
        "rpyc>=6.0.1,<7" \
        "pyquaternion>=0.9.9,<1" \
        "opencv-contrib-python-headless>=4.8.0.74,<5" \
    && git clone --filter=blob:none https://github.com/pollen-robotics/reachy2_symbolic_ik.git /opt/reachy2_symbolic_ik \
    && git -C /opt/reachy2_symbolic_ik checkout --detach "${REACHY2_SYMBOLIC_IK_COMMIT}" \
    && python -m pip install --no-cache-dir -e /opt/reachy2_symbolic_ik \
    && git clone --filter=blob:none https://github.com/pollen-robotics/reachy2_mujoco.git /opt/reachy2_mujoco \
    && git -C /opt/reachy2_mujoco checkout --detach "${REACHY2_MUJOCO_COMMIT}" \
    && grep -q 'description/mjcf/desk_scene.xml' /opt/reachy2_mujoco/reachy2_mujoco/reachy2_mujoco/reachy_mujoco.py \
    && sed -i 's#description/mjcf/desk_scene.xml#description/mjcf/table_scene.xml#' /opt/reachy2_mujoco/reachy2_mujoco/reachy2_mujoco/reachy_mujoco.py \
    && sed -i 's#<body pos="0.7 0 0" name="table"#<body pos="3.0 0 0" name="table"#' /opt/reachy2_mujoco/reachy2_mujoco/description/mjcf/table_scene.xml \
    && sed -i 's#<body name="goal" pos="0.45 -0.4 0.65"#<body name="goal" pos="3.0 -0.4 0.65"#' /opt/reachy2_mujoco/reachy2_mujoco/description/mjcf/table_scene.xml \
    && sed -i 's#                self._update()#                self.mobile_base._update()#' /opt/reachy2_mujoco/reachy2_mujoco/reachy2_mujoco/reachy_mujoco.py \
    && sed -i '/                mujoco.mj_step(self._model, self._data, 20)/i\                loop_started = time.monotonic()' /opt/reachy2_mujoco/reachy2_mujoco/reachy2_mujoco/reachy_mujoco.py \
    && sed -i '/                viewer.sync()/a\                time.sleep(max(0.0, 0.02 - (time.monotonic() - loop_started)))' /opt/reachy2_mujoco/reachy2_mujoco/reachy2_mujoco/reachy_mujoco.py \
    && sed -i '/with mujoco.viewer.launch_passive(self._model, self._data, show_left_ui=False, show_right_ui=False) as viewer:/a\            viewer.cam.azimuth = 135\n            viewer.cam.elevation = -12\n            viewer.cam.distance = 2.35\n            viewer.cam.lookat[:] = [0.18, 0.0, 0.62]' /opt/reachy2_mujoco/reachy2_mujoco/reachy2_mujoco/reachy_mujoco.py \
    && python -m pip install --no-cache-dir --no-deps -e /opt/reachy2_mujoco \
    && rm -rf /root/.cache/pip /opt/reachy2_mujoco/.git /opt/reachy2_symbolic_ik/.git

COPY docker/reachy2-minimal/entrypoint.sh /usr/local/bin/reachy2-minimal
COPY docker/reachy2-minimal/versions.env /etc/reachy2-minimal-versions
RUN chmod +x /usr/local/bin/reachy2-minimal

EXPOSE 18861
ENTRYPOINT ["/usr/local/bin/reachy2-minimal"]

FROM runtime AS proof
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

FROM runtime AS default
