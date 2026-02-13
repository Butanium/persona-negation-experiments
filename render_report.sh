#!/usr/bin/env bash
cd "$(dirname "$0")/article" && uv run quarto preview index.qmd --port 4242 --no-browse
