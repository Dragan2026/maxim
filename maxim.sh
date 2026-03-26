#!/bin/bash
# Quick launcher (no install needed — uses system PyQt5)
cd "$(dirname "$0")"
exec python3 -m maxim.main "$@"
