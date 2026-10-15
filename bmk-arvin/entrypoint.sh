#!/bin/sh
set -eu
mkdir -p "${DATA_DIR:-/data}"
chown shop:shop "${DATA_DIR:-/data}"
exec runuser -u shop -- python server.py
