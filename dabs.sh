#!/bin/sh

docker run -it --rm -v "$(pwd)":/abs/workdir/ app_build_suite:latest $@
