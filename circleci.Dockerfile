FROM gsoci.azurecr.io/giantswarm/conftest:v0.63.0 AS conftest

FROM gsoci.azurecr.io/giantswarm/app-build-suite:1.2.9

COPY --from=conftest /usr/local/bin/conftest /usr/local/bin/conftest

RUN apt-get update && apt-get install -y openssh-client curl jq

# Setup ssh config for github.com
RUN mkdir -p ~/.ssh &&\
    chmod 700 ~/.ssh &&\
    ssh-keyscan github.com >> ~/.ssh/known_hosts &&\
    printf "Host github.com\n IdentitiesOnly yes\n IdentityFile ~/.ssh/id_rsa\n" >> ~/.ssh/config &&\
    chmod 600 ~/.ssh/*
