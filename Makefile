# Image URL to use all building/pushing image targets
IMG ?= app_build_suite
#IMG ?= quay.io/giantswarm/app_build_suite

export VER ?= $(shell git describe 2>/dev/null || echo "0.0.0")
export COMMIT ?= $(shell git rev-parse HEAD 2>/dev/null || echo "0000000")
export SHORT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "0000000")
export DATE ?= $(shell date '+%FT%T%:z')

IMG_VER ?= ${VER}-${SHORT_COMMIT}

.PHONY: all docker-build docker-push docker-build-test test docker-test

all: docker-build

# Build the docker image from locally built binary
docker-build:
	docker build --build-arg ver=${VER} --build-arg commit=${COMMIT} . -t ${IMG}:latest -t ${IMG}:${IMG_VER}

# Push the docker image
docker-push:
	docker push ${IMG}:latest
	docker push ${IMG}:${IMG_VER}

docker-build-test: docker-build
	docker build --build-arg ver=${VER} --build-arg commit=${COMMIT} -f testrunner.Dockerfile . -t ${IMG}-test:latest

test:
	pipenv run pytest --cov app_build_suite --log-cli-level info tests/

docker-test: docker-build-test
	docker run -it --rm ${IMG}-test:latest
