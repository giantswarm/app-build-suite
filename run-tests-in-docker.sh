#!/bin/bash -e

pipenv run pre-commit run --all-files
pipenv run pytest "$@"
