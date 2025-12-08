# Image URL to use all building/pushing image targets
IMG ?= gsoci.azurecr.io/giantswarm/app-build-suite

export VER ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")
export COMMIT ?= $(shell git rev-parse HEAD 2>/dev/null || echo "0000000000000000000000000000000000000000")
export SHORT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "0000000")
export DATE ?= $(shell date '+%FT%T%:z')

IMG_VER ?= ${VER}-${COMMIT}

.PHONY: all release release_ver_to_code docker-build docker-build-no-version docker-push docker-build-test test docker-test docker-test-ci

check_defined = \
    $(strip $(foreach 1,$1, \
        $(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
    $(if $(value $1),, \
      $(error Undefined $1$(if $2, ($2))))

all: docker-build

release: docker-test release_ver_to_code
	git add --force app_build_suite/version.py
	git add dabs.sh setup.py circleci.Dockerfile
	git commit -m "Release ${TAG}" --no-verify
	git tag ${TAG}
	docker build . -t ${IMG}:latest -t ${IMG}:${TAG}
	mv dabs.sh.back dabs.sh
	export NEXT=$(shell uv run pysemver bump patch $${TAG#v}) && echo "build_ver = \"v$${NEXT}-dev\"" > app_build_suite/version.py
	git add dabs.sh
	git add --force app_build_suite/version.py
	git commit -m "Post-release version set for ${TAG}" --no-verify

release_ver_to_code:
	$(call check_defined, TAG)
	sed -i 's/version\=".*"/version\="'${TAG}'"/' setup.py
	echo "build_ver = \"${TAG}\"" > app_build_suite/version.py
	$(eval IMG_VER := ${TAG})
	cp dabs.sh dabs.sh.back
	sed -i "s/:-\".*\"/:-\"$${TAG#v}\"/" dabs.sh
	sed -i "3s/:.*/:$${TAG#v}/" circleci.Dockerfile

# Build the docker image from locally built binary
docker-build-no-version:
	docker build . -t ${IMG}:latest -t ${IMG}:${IMG_VER}

docker-build:
	echo "build_ver = \"${VER}-${COMMIT}\"" > app_build_suite/version.py
	docker build . -t ${IMG}:latest -t ${IMG}:${IMG_VER}

# Push the docker image
docker-push: docker-build
	docker push ${IMG}:${IMG_VER}

docker-build-test: docker-build
	docker build -f testrunner.Dockerfile . -t ${IMG}-test:latest

test-command = --cov app_build_suite --log-cli-level info tests/
test-command-ci = --cov-report=xml $(test-command)
test-docker-args = run -it --rm -v ${PWD}/.coverage/:/abs/.coverage/
test-docker-run = docker $(test-docker-args) ${IMG}-test:latest

test:
	uv run python -m pytest $(test-command)

test-ci:
	uv run python -m pytest $(test-command-ci)

docker-test: docker-build-test
	$(test-docker-run) $(test-command)

docker-test-ci: docker-build-test
	$(test-docker-run) $(test-command-ci)
