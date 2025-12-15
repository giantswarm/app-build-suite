FROM gsoci.azurecr.io/giantswarm/python:3.13.5-slim AS binaries

# renovate: datasource=github-releases depName=helm/helm
ARG HELM_VER=v3.19.4
# renovate: datasource=github-releases depName=helm/chart-testing
ARG CT_VER=v3.14.0
# renovate: datasource=github-releases depName=stackrox/kube-linter
ARG KUBELINTER_VER=v0.7.6

ARG KUBECTL_VER=v1.28.4

RUN apt-get update && apt-get install --no-install-recommends -y wget \
    && mkdir -p /binaries \
    && wget -qO - https://get.helm.sh/helm-${HELM_VER}-linux-amd64.tar.gz | \
    tar -C /binaries --strip-components 1 -xvzf - linux-amd64/helm \
    && wget -qO - https://github.com/helm/chart-testing/releases/download/${CT_VER}/chart-testing_${CT_VER##v}_linux_amd64.tar.gz | \
    tar -C /binaries -xvzf - ct etc/lintconf.yaml etc/chart_schema.yaml && mv /binaries/etc /etc/ct \
    && wget -qO - https://github.com/stackrox/kube-linter/releases/download/${KUBELINTER_VER}/kube-linter-linux.tar.gz | \
    tar -C /binaries -xvzf - \
    && wget -P /binaries https://dl.k8s.io/release/${KUBECTL_VER}/bin/linux/amd64/kubectl && chmod +x /binaries/kubectl


COPY container-entrypoint.sh /binaries

RUN chmod +x /binaries/*


FROM gsoci.azurecr.io/giantswarm/python:3.13.5-slim AS base

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /bin/uv
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ABS_DIR="/abs"

WORKDIR $ABS_DIR


FROM base AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY README.md ${ABS_DIR}/
COPY resources/ ${ABS_DIR}/resources/
COPY app_build_suite/ ${ABS_DIR}/app_build_suite/

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked

FROM base

ARG CT_YAMALE_VER="4.0.2"
ARG CT_YAMLLINT_VER="1.26.3"

ENV USE_UID=0 \
    USE_GID=0 \
    PATH="${ABS_DIR}/.venv/bin:/usr/local/bin:$PATH" \
    PYTHONPATH=$ABS_DIR

# install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y git sudo && \
    # svg processing for icon validation
    apt-get install --no-install-recommends -y libpangocairo-1.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# dependencies for ct
RUN uv pip install --system yamllint==${CT_YAMLLINT_VER} yamale==${CT_YAMALE_VER}

COPY --from=binaries /binaries/* /usr/local/bin/
COPY --from=binaries /etc/ct /etc/ct

# we assume the user will be using UID==1000 and GID=1000; if that's not true, we'll run `chown`
# in the container's startup script
COPY --from=builder --chown=1000:1000 $ABS_DIR $ABS_DIR

WORKDIR $ABS_DIR/workdir

ENTRYPOINT ["container-entrypoint.sh"]

CMD ["-h"]
