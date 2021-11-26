#!/bin/sh

set -e

script=fritzbox_dyndns_update.py
cfg="${script%.py}.ini"
unit="${script%.py}.service"


uid=`id -u`
gid=`id -g`
target=/usr/local/lib/fritzbox_dyndns_update

sudo install -m755 "-o$uid" "-g$gid" -d "$target"
virtualenv $target
$target/bin/pip install fritzconnection ConfigArgParse
install -m755 "$script" "$target/$script"
sudo chown -R 0:0 "$target"

if ! [ -f "/etc/$cfg" ] ; then
	sudo install -m600 -o0 -g0 "$cfg" "/etc/$cfg"
fi

sudo install -m644 "$unit" "/etc/systemd/system/$unit"
