#!/bin/bash

set -euo pipefail

if [ -f /local/.deployed ]
then
    exit 0
fi

NODE="$(hostname -s)"

systemctl start pve-cluster
mkdir "/etc/pve/nodes/$NODE"
mv /etc/pve/nodes/node/* "/etc/pve/nodes/$NODE"
rmdir /etc/pve/nodes/node
pvecm updatecerts -f
chpasswd <<< "root:$1"

while ! nc -z 10.10.1.1 8006
do
  echo "Waiting for the first node to be ready…"
  sleep 5
done

sleep $(($(echo "$NODE" | grep -oE "[0-9]+") * 15))

expect << DONE
  spawn pvecm add 10.10.1.1
  expect :
  send -- "$1\r"
  expect -ex ?
  send yes\r
  expect eof
DONE

systemctl unmask pveproxy
systemctl restart pve{-firewall,-ha-crm,-ha-lrm,scheduler,statd,proxy}.service

touch /local/.deployed
