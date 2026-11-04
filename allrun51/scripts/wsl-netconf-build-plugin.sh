#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_dir="$project_dir/netconf/plugins"
mkdir -p "$plugin_dir"

pkg-config --exists sysrepo libyang
cc $(pkg-config --cflags sysrepo libyang) \
  -std=c11 -Wall -Wextra -Werror -fPIC -shared \
  "$project_dir/netconf/green_snapshot_plugin.c" \
  -o "$plugin_dir/green_snapshot_plugin.so" \
  $(pkg-config --libs sysrepo libyang)

printf 'Built %s\n' "$plugin_dir/green_snapshot_plugin.so"