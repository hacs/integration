#!/usr/bin/env bash
set -e
cd /hacs || exit 1

ls -la

exec python3 action.py
echo $?