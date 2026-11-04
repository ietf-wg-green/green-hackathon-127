#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
yang_dir="$project_dir/yang"
multiarch_triplet="$(cc -print-multiarch)"
if [[ -z "$multiarch_triplet" ]]; then
  echo "Could not determine the system multiarch library directory." >&2
  exit 1
fi
install -d -o root -g root -m 0755 \
  "/usr/lib/$multiarch_triplet/sysrepo-plugind/plugins"

install_module_if_missing() {
  local module_name="$1"
  local module_file="$2"
  if ! sysrepoctl -l | awk -v name="$module_name" '$1 == name { found=1 } END { exit !found }'; then
    sysrepoctl -a -i "$yang_dir/$module_file" -s "$yang_dir"
  fi
}

install_module_if_missing ietf-inet-types ietf-inet-types@2013-07-15.yang
install_module_if_missing ietf-yang-types ietf-yang-types@2013-07-15.yang
install_module_if_missing iana-hardware iana-hardware@2018-03-13.yang
install_module_if_missing ietf-hardware ietf-hardware@2018-03-13.yang
install_module_if_missing iana-power-and-energy iana-power-and-energy@2026-07-02.yang
install_module_if_missing ietf-power-and-energy ietf-power-and-energy@2026-07-02.yang
sysrepocfg --edit="$yang_dir/hardware-hierarchy.xml" --datastore startup --format xml --module ietf-hardware
sysrepocfg --copy-from startup --module ietf-hardware
if ! sysrepoctl -l | awk -F'|' '$1 ~ /iana-crypt-hash/ && $3 ~ /I/ { found=1 } END { exit !found }'; then
  sysrepoctl -i /usr/share/yang/modules/netopeer2/iana-crypt-hash@2014-08-06.yang
fi
if ! sysrepoctl -l | awk -F'|' '$1 ~ /iana-crypt-hash/ && $7 ~ /crypt-hash-sha-512/ { found=1 } END { exit !found }'; then
  sysrepoctl -c iana-crypt-hash -e crypt-hash-sha-512 -a
fi

export NP2_MODULE_DIR=/usr/share/yang/modules/netopeer2
export NP2_MODULE_PERMS=660
export NP2_MODULE_OWNER=root
export NP2_MODULE_GROUP=netconf
export SYSREPOCTL_EXECUTABLE=/usr/bin/sysrepoctl
export SYSREPOCFG_EXECUTABLE=/usr/bin/sysrepocfg

/usr/share/netopeer2/setup.sh
/usr/share/netopeer2/merge_hostkey.sh
/usr/share/netopeer2/merge_config.sh

smoke_password="$(openssl rand -hex 24)"
password_salt="$(openssl rand -hex 8)"
password_hash="$(openssl passwd -6 -salt "$password_salt" "$smoke_password")"
if id allrun51-smoke >/dev/null 2>&1; then
  usermod --password "$password_hash" allrun51-smoke
else
  useradd --system --no-create-home --shell /usr/sbin/nologin --password "$password_hash" allrun51-smoke
fi
netconf_host="$(hostname -I | awk '{print $1}')"
netconf_host="${netconf_host:-127.0.0.1}"

connection_config="$project_dir/runtime/netconf/connection.env"
mkdir -p "$(dirname -- "$connection_config")"
cat > "$connection_config" <<EOF
NETCONF_HOST=$netconf_host
NETCONF_PORT=830
NETCONF_USERNAME=allrun51-smoke
NETCONF_PASSWORD=$smoke_password
EOF
chmod 600 "$connection_config"

mkdir -p "$project_dir/runtime/netconf"
auth_xml="$(mktemp "$project_dir/runtime/netconf/netconf-auth.XXXXXX")"
trap 'rm -f "$auth_xml"' EXIT
cat > "$auth_xml" <<EOF
<netconf-server xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-server">
  <listen>
    <endpoint>
      <name>default-ssh</name>
      <ssh>
        <ssh-server-parameters>
          <client-authentication>
            <supported-authentication-methods>
              <passsword/>
            </supported-authentication-methods>
            <users>
              <user>
                <name>allrun51-smoke</name>
                <password>$password_hash</password>
              </user>
            </users>
          </client-authentication>
        </ssh-server-parameters>
      </ssh>
    </endpoint>
  </listen>
</netconf-server>
EOF
/usr/bin/sysrepocfg --edit="$auth_xml" --datastore startup --format xml --module ietf-netconf-server
/usr/bin/sysrepocfg --copy-from startup --module ietf-netconf-server
rm -f "$auth_xml"
trap - EXIT

printf 'Installed required YANG modules and local ncclient password user.\n'
sysrepoctl -l | grep -E '^(ietf-power-and-energy|iana-power-and-energy|ietf-hardware|iana-hardware)[[:space:]]'