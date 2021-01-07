#!/bin/sh

docker run -it --rm \
  -e USE_UID="$(id -u "${USER}")" \
  -e USE_GID="$(id -g "${USER}")" \
  -v "$(pwd)":/abs/workdir/ \
  --network host \
  quay.io/giantswarm/app-build-suite:v0.1.2 "$@"
