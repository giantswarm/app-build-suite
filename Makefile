# Image URL to use all building/pushing image targets
IMG ?= quay.io/giantswarm/app-build-suite

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

test-command = --cov app_build_suite --log-cli-level info tests/
test-command-ci = --cov-report=xml $(test-command)
test-docker-args = run -it --rm -v ${PWD}/.coverage/:/abs/.coverage/
test-docker-run = docker $(test-docker-args) ${IMG}-test:latest
test-docker-run-ci = docker $(test-docker-args) -v ${PWD}/.git:/abs/.git/ ${IMG}-test:latest

test:
	pipenv run pytest $(test-command)

docker-test: docker-build-test
	$(test-docker-run) $(test-command)

docker-test-ci: docker-build-test
	$(test-docker-run-ci) $(test-command-ci)
