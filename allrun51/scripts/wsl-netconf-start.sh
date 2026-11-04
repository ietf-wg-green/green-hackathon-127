#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_dir="$project_dir/netconf/plugins"
state_file="$project_dir/runtime/operational.json"
trace_file="$project_dir/logs/netconf-trace.log"
mkdir -p "$(dirname -- "$state_file")" "$(dirname -- "$trace_file")"

systemctl stop netopeer2.service sysrepo-plugind.service
"$project_dir/scripts/wsl-netconf-install.sh"
"$project_dir/scripts/wsl-netconf-build-plugin.sh"

systemctl set-environment \
  "SRPD_PLUGINS_PATH=$plugin_dir" \
  "GREEN_NETCONF_STATE_FILE=$state_file" \
  "GREEN_NETCONF_TRACE_FILE=$trace_file"
systemctl restart sysrepo-plugind.service
systemctl restart netopeer2.service

for attempt in $(seq 1 15); do
  if ss -ltn | awk '$4 ~ /:830$/ { found=1 } END { exit !found }'; then
    echo "Netopeer2 is listening on TCP port 830"
    exit 0
  fi
  sleep 1
done

echo "Netopeer2 did not open TCP port 830." >&2
exit 1