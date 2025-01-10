#!/bin/sh
# Run integration tests with spread sequentially on all the systems, using
# multiple workers per system. This mode is suitable to run on a single
# quad-core CPU with 8GB of RAM and no desktop session.
set -xeu

if test -z "$(command -v spread)"; then
	echo "You need to install spread from https://github.com/snapcore/spread with the Go compiler and the command: go install github.com/snapcore/spread/cmd/spread@latest" >&2
	exit 1
fi

if test -z "$(command -v image-garden)"; then
	echo "You need to install image-garden from https://gitlab.com/zygoon/image-garden: make install prefix=/usr/local" >&2
	exit 1
fi

rm -rf spread-logs spread-artifacts
mkdir -p spread-logs
for system in \
	opensuse-cloud-tumbleweed \
	debian-cloud-12 \
	debian-cloud-13 \
	ubuntu-cloud-22.04 \
	ubuntu-cloud-24.04 \
	ubuntu-cloud-24.10 \
	ubuntu-cloud-25.04; do
	if ! spread -artifacts ./spread-artifacts -v "$system" | tee spread-logs/"$system".log; then
		echo "Spread exited with code $?" >spread-logs/"$system".failed
	fi
done
