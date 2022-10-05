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

pvecm create "$2"
systemctl unmask pveproxy
systemctl start pve{-firewall,-ha-crm,-ha-lrm,proxy,scheduler,statd}.service

touch /local/.deployed
