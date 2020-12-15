#!/bin/bash -e

if [ $# -eq 1 ] && [ "$1" == "versions" ]; then
  echo "-> python env:"
  python --version
  pip --version
  pipenv --version
  echo
  echo "-> kubectl:"
  kubectl version --client
  echo
  echo "-> helm:"
  helm version
  echo
  echo "-> ct:"
  ct version
  echo
  echo "-> apptestctl:"
  apptestctl version
  exit 0
fi

if [ "${USE_UID:-0}" -ne 0 ] && [ "${USE_GID:-0}" -ne 0 ]; then
  groupadd -f -g "$USE_UID" abs
  useradd -g "$USE_GID" -M -l -u "$USE_UID" abs -d "$ABS_DIR" -s /bin/bash || true
fi

chown -R "$USE_UID":"$USE_GID" "$ABS_DIR"
sudo --preserve-env=PYTHONPATH,PATH -g "#$USE_GID" -u "#$USE_UID" -- python -m app_build_suite "$@"
