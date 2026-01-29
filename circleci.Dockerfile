FROM gsoci.azurecr.io/giantswarm/conftest:v0.66.0 AS conftest

FROM gsoci.azurecr.io/giantswarm/app-build-suite:1.6.0

COPY --from=conftest /usr/local/bin/conftest /usr/local/bin/conftest

RUN apt-get update && apt-get install -y openssh-client curl jq wget gh

RUN wget https://github.com/Link-/gh-token/releases/download/v2.0.6/linux-amd64 -O /usr/bin/gh-token && chmod 700 /usr/bin/gh-token

# Setup ssh config for github.com
RUN mkdir -p ~/.ssh &&\
    chmod 700 ~/.ssh &&\
    ssh-keyscan github.com >> ~/.ssh/known_hosts &&\
    printf "Host github.com\n IdentitiesOnly yes\n IdentityFile ~/.ssh/id_rsa\n" >> ~/.ssh/config &&\
    chmod 600 ~/.ssh/*
