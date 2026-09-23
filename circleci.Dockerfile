# The base is the plain app-build-suite image of the same build: the CircleCI
# job passes ABS_VERSION=${DOCKER_IMAGE_VERSION} (the architect orb's version
# without the -circleci tag-suffix) and requires the job that pushed that image.
# The default only serves a local `docker build -f circleci.Dockerfile .`.
ARG ABS_VERSION=2.4.0
FROM gsoci.azurecr.io/giantswarm/app-build-suite:${ABS_VERSION}

RUN apt-get update && apt-get install -y openssh-client curl jq wget gh

RUN wget https://github.com/Link-/gh-token/releases/download/v2.0.6/linux-amd64 -O /usr/bin/gh-token && chmod 700 /usr/bin/gh-token

# renovate: datasource=github-releases depName=sigstore/cosign
ARG COSIGN_VER=v3.0.6

# Install cosign for keyless OIDC chart signing in CircleCI. The architect orb's
# `cosign-prepare` step assumes `cosign` is on PATH; without it, every
# `push-to-app-catalog` job that uses this executor and the orb's default
# `sign: true` fails with `cosign: command not found`. SHA-256 verified against
# the upstream `cosign_checksums.txt` from the same release tag.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64|arm64) ;; *) echo "unsupported arch $arch" >&2; exit 1 ;; esac; \
    base="https://github.com/sigstore/cosign/releases/download/${COSIGN_VER}"; \
    curl --silent --show-error --fail --location --retry 5 --retry-delay 2 \
    -o /tmp/cosign "${base}/cosign-linux-${arch}"; \
    curl --silent --show-error --fail --location --retry 5 --retry-delay 2 \
    -o /tmp/cosign_checksums.txt "${base}/cosign_checksums.txt"; \
    expected="$(awk -v f="cosign-linux-${arch}" '$2 == f {print $1}' /tmp/cosign_checksums.txt)"; \
    [ -n "$expected" ] || { echo "no checksum for cosign-linux-${arch}" >&2; exit 1; }; \
    echo "${expected}  /tmp/cosign" | sha256sum -c -; \
    install -m 0755 /tmp/cosign /usr/local/bin/cosign; \
    rm -f /tmp/cosign /tmp/cosign_checksums.txt; \
    cosign version

# renovate: datasource=github-releases depName=giantswarm/gitsemver
ARG GITSEMVER_VER=v3.0.0

# Install gitsemver to compute chart versions from git state in CircleCI jobs.
# No upstream checksums file is published, but v3.0.0 and later ship a sigstore
# bundle per asset, signed keylessly by the gitsemver CircleCI project. The
# identity regexp pins that project's id; the pipeline-definition id that
# follows it in the certificate SAN can change between releases.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64|arm64) ;; *) echo "unsupported arch $arch" >&2; exit 1 ;; esac; \
    base="https://github.com/giantswarm/gitsemver/releases/download/${GITSEMVER_VER}"; \
    curl --silent --show-error --fail --location --retry 5 --retry-delay 2 \
    -o /tmp/gitsemver "${base}/gitsemver-linux-${arch}"; \
    curl --silent --show-error --fail --location --retry 5 --retry-delay 2 \
    -o /tmp/gitsemver.bundle "${base}/gitsemver-linux-${arch}.bundle"; \
    cosign verify-blob --bundle /tmp/gitsemver.bundle \
    --certificate-oidc-issuer https://oidc.circleci.com \
    --certificate-identity-regexp '^https://circleci[.]com/api/v2/projects/45b06616-51d8-4608-ac84-fdee808d7a3d/' \
    /tmp/gitsemver; \
    install -m 0755 /tmp/gitsemver /usr/local/bin/gitsemver; \
    rm -f /tmp/gitsemver /tmp/gitsemver.bundle; \
    gitsemver --version

# Setup ssh config for github.com
RUN mkdir -p ~/.ssh &&\
    chmod 700 ~/.ssh &&\
    ssh-keyscan github.com >> ~/.ssh/known_hosts &&\
    printf "Host github.com\n IdentitiesOnly yes\n IdentityFile ~/.ssh/id_rsa\n" >> ~/.ssh/config &&\
    chmod 600 ~/.ssh/*
