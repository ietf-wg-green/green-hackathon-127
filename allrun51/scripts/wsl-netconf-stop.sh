#!/usr/bin/env bash
set -euo pipefail

systemctl stop netopeer2.service sysrepo-plugind.service
systemctl unset-environment SRPD_PLUGINS_PATH GREEN_NETCONF_STATE_FILE GREEN_NETCONF_TRACE_FILE
echo "Stopped the allrun51 NETCONF services."