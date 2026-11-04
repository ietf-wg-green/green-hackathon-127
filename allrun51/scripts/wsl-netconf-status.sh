#!/usr/bin/env bash
set -euo pipefail

source /etc/os-release
printf 'WSL distribution: %s\n' "$PRETTY_NAME"
printf 'libyang: %s\n' "$(pkg-config --modversion libyang 2>/dev/null || echo unavailable)"
printf 'Sysrepo: %s\n' "$(pkg-config --modversion sysrepo 2>/dev/null || echo unavailable)"
printf 'Netopeer2: %s\n' "$(dpkg-query -W -f='${Version}' netopeer2 2>/dev/null || echo unavailable)"

for service in sysrepo-plugind.service netopeer2.service; do
  if systemctl is-active --quiet "$service"; then
    printf '%s: running\n' "$service"
  else
    printf '%s: stopped\n' "$service"
  fi
done
sysrepoctl -l | grep -E '^(ietf-power-and-energy|iana-power-and-energy|ietf-hardware|iana-hardware|ietf-inet-types|ietf-yang-types)[[:space:]]' || true
ss -ltn | awk '$4 ~ /:830$/ { print "NETCONF listener: " $4 }'
printf 'WSL address fallback: %s\n' "$(hostname -I | awk '{print $1}')"