FROM gsoci.azurecr.io/giantswarm/conftest:v0.68.2 AS conftest

FROM gsoci.azurecr.io/giantswarm/app-build-suite:1.8.2

COPY --from=conftest /usr/local/bin/conftest /usr/local/bin/conftest

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

# Setup ssh config for github.com
RUN mkdir -p ~/.ssh &&\
    chmod 700 ~/.ssh &&\
    ssh-keyscan github.com >> ~/.ssh/known_hosts &&\
    printf "Host github.com\n IdentitiesOnly yes\n IdentityFile ~/.ssh/id_rsa\n" >> ~/.ssh/config &&\
    chmod 600 ~/.ssh/*
