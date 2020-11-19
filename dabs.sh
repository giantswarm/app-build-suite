#!/bin/sh

docker run -it --rm \
  -e USE_UID="$(id -u "${USER}")" \
  -e USE_GID="$(id -g "${USER}")" \
  -v "$(pwd)":/abs/workdir/ \
  quay.io/giantswarm/app-build-suite:latest "$@"
