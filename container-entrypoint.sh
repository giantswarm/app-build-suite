#!/bin/bash -e

if [ $# -eq 1 ] && [ "$1" == "versions" ]; then
    echo "-> python env:"
    python --version
    uv --version
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
    echo "-> kube-linter:"
    kube-linter version
    echo
    exit 0
fi

if [ "${USE_UID:-0}" -ne 0 ] && [ "${USE_GID:-0}" -ne 0 ]; then
    groupadd -f -g "$USE_GID" abs
    useradd -g "$USE_GID" -M -l -u "$USE_UID" abs -d "$ABS_DIR" -s /bin/bash || true
fi

if [ "${USE_UID:-0}" -ne 1000 ] || [ "${USE_GID:-0}" -ne 1000 ]; then
    chown -R "$USE_UID":"$USE_GID" "$ABS_DIR"
fi
sudo --preserve-env=PYTHONPATH,PATH -g "#$USE_GID" -u "#$USE_UID" -- python -m app_build_suite "$@"
