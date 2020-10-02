FROM python:3.8.6-alpine3.12

ARG WORK_DIR="/tmp/install"
ARG ABS_DIR="/abs"
ENV HELM_VER="3.3.4"
ENV KUBECTL_VER="1.18.9"
ENV CT_VER="3.1.1"

# install dependencies
RUN apk add --no-cache curl git
RUN mkdir $WORK_DIR
WORKDIR $WORK_DIR
# pip prerequesties
RUN pip install yamllint==1.25.0 yamale==3.0.4 pipenv==2020.8.13
# kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VER}/bin/linux/amd64/kubectl \
    && install kubectl /usr/local/bin && rm kubectl && kubectl version --client=true
# helm
RUN curl -L https://get.helm.sh/helm-v3.3.4-linux-amd64.tar.gz -o ./helm.tar.gz \
    && tar zxf helm.tar.gz && install linux-amd64/helm /usr/local/bin \
    && rm -rf linux-amd64/ && rm helm.tar.gz && helm version
# ct
RUN curl -L https://github.com/helm/chart-testing/releases/download/v${CT_VER}/chart-testing_${CT_VER}_linux_amd64.tar.gz \
    -o ct.tar.gz && tar zxf ct.tar.gz && install ct /usr/local/bin && mkdir /etc/ct \
    && mv ./etc/* /etc/ct/ && rm ct && rm ct.tar.gz && ct version
# cleanup
RUN rm -rf $WORK_DIR

RUN adduser --disabled-password --home $ABS_DIR --uid 1001 abs
WORKDIR $ABS_DIR
RUN apk add --no-cache gcc musl-dev
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install -v --deploy
COPY setup.py setup.py
COPY app_build_suite/ app_build_suite/
RUN chown -R abs.abs .
USER abs
ENTRYPOINT ["pipenv", "run", "python", "-m", "app_build_suite"]
CMD ["-h"]
