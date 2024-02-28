FROM quay.io/giantswarm/python:3.10.3-slim AS binaries

# renovate: datasource=github-releases depName=helm/helm
ARG HELM_VER=v3.14.2
# renovate: datasource=github-releases depName=helm/chart-testing
ARG CT_VER=v3.10.1
# renovate: datasource=github-releases depName=stackrox/kube-linter
ARG KUBELINTER_VER=v0.6.8

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


FROM quay.io/giantswarm/python:3.10.3-slim AS base

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    ABS_DIR="/abs" \
    PIPENV_VER="2023.7.11"

RUN pip install --no-cache-dir pipenv==${PIPENV_VER}

WORKDIR $ABS_DIR


FROM base as builder

# pip prerequesties
RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY Pipfile Pipfile.lock ./

RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --clear


FROM base

ARG CT_YAMALE_VER="4.0.2"
ARG CT_YAMLLINT_VER="1.26.3"

ENV USE_UID=0 \
    USE_GID=0 \
    PATH="${ABS_DIR}/.venv/bin:$PATH" \
    PYTHONPATH=$ABS_DIR

# install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y git sudo && \
    # svg processing for icon validation
    apt-get install --no-install-recommends -y libpangocairo-1.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# pip dependencies for ct
RUN pip install yamllint==${CT_YAMLLINT_VER} yamale==${CT_YAMALE_VER}

COPY --from=builder ${ABS_DIR}/.venv ${ABS_DIR}/.venv

COPY --from=binaries /binaries/* /usr/local/bin/
COPY --from=binaries /etc/ct /etc/ct

COPY resources/ ${ABS_DIR}/resources/
COPY app_build_suite/ ${ABS_DIR}/app_build_suite/

WORKDIR $ABS_DIR/workdir

# we assume the user will be using UID==1000 and GID=1000; if that's not true, we'll run `chown`
# in the container's startup script
RUN chown -R 1000:1000 $ABS_DIR

ENTRYPOINT ["container-entrypoint.sh"]

CMD ["-h"]
