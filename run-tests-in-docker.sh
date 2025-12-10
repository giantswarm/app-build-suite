#!/bin/bash -e

uv run pre-commit run --all-files
uv run pytest "$@"
