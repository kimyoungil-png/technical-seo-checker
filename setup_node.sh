#!/bin/bash

set -e

NODE_VERSION="22.19.0"
ARCH="x64"

cd /tmp

curl -fsSLO "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz"

tar -xf "node-v${NODE_VERSION}-linux-${ARCH}.tar.xz"

mkdir -p "$HOME/node22"

cp -r "node-v${NODE_VERSION}-linux-${ARCH}/"* "$HOME/node22/"
