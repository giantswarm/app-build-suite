FROM alpine:3.13.2 AS binaries

ARG HELM_VER="3.5.2"
ARG KUBECTL_VER="1.20.4"
ARG CT_VER="3.3.1"
ARG APPTESTCTL_VER="0.7.0"
ARG DOCKER_VER="20.10.3"
# upgrade to kind 0.10.0 held, as it defaults to kubernetes 1.20
ARG KIND_VER="0.9.0"
ARG KUBELINTER_VER="0.1.6"

RUN apk add --no-cache ca-certificates curl \
    && mkdir -p /binaries \
    && curl -SL https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VER}/bin/linux/amd64/kubectl -o /binaries/kubectl \
    && curl -SL https://get.helm.sh/helm-v${HELM_VER}-linux-amd64.tar.gz | \
       tar -C /binaries --strip-components 1 -xvzf - linux-amd64/helm \
    && curl -SL https://github.com/giantswarm/apptestctl/releases/download/v${APPTESTCTL_VER}/apptestctl-v${APPTESTCTL_VER}-linux-amd64.tar.gz | \
       tar -C /binaries --strip-components 1 -xvzf - apptestctl-v${APPTESTCTL_VER}-linux-amd64/apptestctl \
    && curl -SL https://github.com/helm/chart-testing/releases/download/v${CT_VER}/chart-testing_${CT_VER}_linux_amd64.tar.gz | \
       tar -C /binaries -xvzf - ct etc/lintconf.yaml etc/chart_schema.yaml && mv /binaries/etc /etc/ct \
    && curl -SL https://github.com/stackrox/kube-linter/releases/download/${KUBELINTER_VER}/kube-linter-linux.tar.gz | \
       tar -C /binaries -xvzf - \
    && curl -SL https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VER}.tgz | \
       tar -C /binaries --strip-components 1 -xvzf - docker/docker \
    && curl -SL https://github.com/kubernetes-sigs/kind/releases/download/v${KIND_VER}/kind-linux-amd64 -o /binaries/kind

COPY container-entrypoint.sh /binaries

RUN chmod +x /binaries/*


FROM quay.io/giantswarm/python:3.8.6-slim AS base

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    ABS_DIR="/abs" \
    PIPENV_VER="2020.11.15"

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

ARG CT_YAMALE_VER="3.0.4"
ARG CT_YAMLLINT_VER="1.25.0"

ENV USE_UID=0 \
    USE_GID=0 \
    PATH="${ABS_DIR}/.venv/bin:$PATH" \
    PYTHONPATH=$ABS_DIR

# install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y git sudo && \
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
