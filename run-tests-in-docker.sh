#!/bin/bash -e

#if [ ${USE_UID:-0} -ne 0 ] && [ ${USE_GID:-0} -ne 0 ]; then
#  groupadd -f -g $USE_UID abs
#  useradd -g $USE_GID -M -l -u $USE_UID abs -d $ABS_DIR -s /bin/bash || true
#fi

#chown -R $USE_UID:$USE_GID $ABS_DIR
#sudo --preserve-env=PYTHONPATH,PATH -g "#$USE_GID" -u "#$USE_UID" -- python -m app_build_suite $@
#pipenv run pre-commit run --all-files
pipenv run pytest $@
