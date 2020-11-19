FROM python:3.8.6-slim AS base

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1
ENV ABS_DIR="/abs"
ENV PIPENV_VER="2020.8.13"
RUN mkdir $ABS_DIR
WORKDIR $ABS_DIR


FROM base as builder
# pip prerequesties
RUN pip install --no-cache-dir pipenv==${PIPENV_VER}
RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --clear


FROM base
ARG WORK_DIR="/tmp/install"
ENV HELM_VER="3.3.4"
ENV KUBECTL_VER="1.18.9"
ENV CT_VER="3.1.1"
ARG CT_YAMALE_VER="3.0.4"
ARG CT_YAMLLINT_VER="1.25.0"
ENV APPTESTCTL_VER="0.4.1"

# install dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y curl git sudo && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN mkdir $WORK_DIR
WORKDIR $WORK_DIR
# kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VER}/bin/linux/amd64/kubectl \
    && install kubectl /usr/local/bin && rm kubectl && kubectl version --client=true
# helm
RUN curl -L https://get.helm.sh/helm-v${HELM_VER}-linux-amd64.tar.gz -o ./helm.tar.gz \
    && tar zxf helm.tar.gz && install linux-amd64/helm /usr/local/bin \
    && rm -rf linux-amd64/ && rm helm.tar.gz && helm version
# ct
RUN curl -L https://github.com/helm/chart-testing/releases/download/v${CT_VER}/chart-testing_${CT_VER}_linux_amd64.tar.gz \
    -o ct.tar.gz && tar zxf ct.tar.gz && install ct /usr/local/bin && mkdir /etc/ct \
    && mv ./etc/* /etc/ct/ && rm ct && rm ct.tar.gz && ct version
# apptestctl
RUN curl -L https://github.com/giantswarm/apptestctl/releases/download/v${APPTESTCTL_VER}/apptestctl-v${APPTESTCTL_VER}-linux-amd64.tar.gz \
    -o apptestctl.tar.gz && tar zxf apptestctl.tar.gz && install apptestctl-v${APPTESTCTL_VER}-linux-amd64/apptestctl /usr/local/bin && \
    rm apptestctl.tar.gz && rm -rf apptestctl-v${APPTESTCTL_VER}-linux-amd64 && apptestctl version
# cleanup
RUN rm -rf $WORK_DIR
# pip dependencies for ct
RUN pip install yamllint==${CT_YAMLLINT_VER} yamale==${CT_YAMALE_VER}

ENV USE_UID=0
ENV USE_GID=0
COPY --from=builder ${ABS_DIR}/.venv ${ABS_DIR}/.venv
ENV PATH="${ABS_DIR}/.venv/bin:$PATH"
RUN mkdir -p $ABS_DIR/workdir
ENV PYTHONPATH=$ABS_DIR
WORKDIR $ABS_DIR/workdir
COPY run-abs-in-docker.sh /usr/local/bin/
COPY resources/ ${ABS_DIR}/resources/
COPY app_build_suite/ ${ABS_DIR}/app_build_suite/
ENTRYPOINT ["run-abs-in-docker.sh"]
CMD ["-h"]
