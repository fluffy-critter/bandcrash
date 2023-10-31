#!/bin/sh
# Build wrapper script

export PATH=$(echo $PATH | sed s,[^:]*/homebrew[^:]*:,,g)
make "$@"
