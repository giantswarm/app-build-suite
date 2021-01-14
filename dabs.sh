#!/bin/sh

DABS_TAG=${DABS_TAG:-"0.1.4"}

docker run -it --rm \
  -e USE_UID="$(id -u "${USER}")" \
  -e USE_GID="$(id -g "${USER}")" \
  -e DOCKER_GID="$(getent group docker | cut -d: -f3)" \
  -v "$(pwd)":/abs/workdir/ \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --network host \
  "quay.io/giantswarm/app-build-suite:${DABS_TAG}" "$@"
