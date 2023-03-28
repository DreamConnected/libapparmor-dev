# vim:syntax=sh
#
#	Copyright (C) 2013 Canonical, Ltd.
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

gendbusprofile()
{
	genprofile --stdin <<EOF
${__dbus_var_decl}
$test {
  @{gen $test}
  $outfile w,
  unix,
  $*
  signal receive peer=unconfined,
}
EOF
	unset __dbus_var_decl
}

# the arguments passed are emitted in the profile's prologue, for
# setting profile variables, e.g.
#	set_dbus_var "@{MY_DBUS_VAR}=stuff"
# the saved variable declaration gets unset after each test run
set_dbus_var()
{
  __dbus_var_decl=$@
}

cleanup_dbus_broker()
{
	rm -f /etc/systemd/system/dbus-apparmor-test.socket
	rm -f /etc/systemd/system/dbus-apparmor-test.service
	# don't stop test execution if systemctl is not available
	systemctl daemon-reload 2>/dev/null || true
}

kill_dbus_broker()
{
	if [ $(systemctl is-active dbus-apparmor-test.service) == "active" ]
	then
		if ! systemctl -q stop dbus-apparmor-test.service
		then
			echo "Failed to stop DBus broker service"
		fi
	fi

	if [ $(systemctl is-active dbus-apparmor-test.socket) == "active" ]
	then
		if ! systemctl -q stop dbus-apparmor-test.socket
		then
			echo "Failed to stop DBus broker socket"
		fi
	fi

	cleanup_dbus_broker
}

start_dbus_broker()
{
	# TODO: remove systemd dependency from DBus Broker tests
	if [ ! -d /run/systemd/system/ ]
	then
		echo "Error: DBus Broker tests require systemd"
		return 1
	fi

	if [ $(which dbus-broker-launch > /dev/null; echo $?) -ne 0 ]
	then
		echo "Error: dbus-broker-launch not available"
		return 1
	fi

	bus_addr=$(mktemp --dry-run /tmp/dbus-XXXXXX)

	dbus_test_socket="
[Unit]
Description=AppArmor D-Bus Broker Test Socket

[Socket]
ListenStream=@$bus_addr
"
	dbus_test_service="
[Unit]
Description=AppArmor D-Bus Broker Test Service
After=dbus-apparmor-test.socket
Requires=dbus-apparmor-test.socket

[Service]
Sockets=dbus-apparmor-test.socket
StartLimitBurst=0
ExecStart=dbus-broker-launch --scope system --audit --config-file=$(pwd)/dbus.conf

[Install]
WantedBy=default.target
"
	echo "$dbus_test_socket" > /etc/systemd/system/dbus-apparmor-test.socket
	echo "$dbus_test_service" > /etc/systemd/system/dbus-apparmor-test.service

	systemctl daemon-reload

	if ! systemctl -q start dbus-apparmor-test
	then
		echo "Error: Failed to start DBus broker launcher"
		return 1
	fi

	do_onexit="kill_dbus_broker"

	export DBUS_SESSION_BUS_ADDRESS="unix:abstract=$bus_addr"
	return 0
}

kill_dbus_daemon()
{
	kill $bus_pid >/dev/null 2>&1 || true
}

start_dbus_daemon()
{
	if [ $(which dbus-daemon > /dev/null; echo $?) -ne 0 ]
	then
		echo "Error: dbus-daemon not available"
		return 1
	fi

	bus_addr=$(mktemp --dry-run /tmp/dbus-XXXXXX)
	out=$(dbus-daemon --fork --print-pid --print-address --address="unix:abstract=$bus_addr" --config-file=dbus.conf)
	if [ $? -ne 0 ]
	then
		echo "Failed to start DBus daemon"
		return 1
	fi

	bus_addr=$(echo $out | cut -d\  -f 1)
	bus_pid=$(echo $out | cut -d\  -f 2)

	# The daemon may error out during initialization. Unfortunately,
	# there's no good way to detect that, but this will work under normal
	# conditions.
	sleep 1
	kill -0 $bus_pid 2>/dev/null
	if [ $? -ne 0 ]
	then
		echo "DBus daemon unexpectedly stopped"
		return 1
	fi

	do_onexit="kill_dbus_daemon"
	export DBUS_SESSION_BUS_ADDRESS=$bus_addr
	return 0
}

bus="session"
dest=com.apparmor.Test
path=/com/apparmor/Test
iface=com.apparmor.Test

# parameters: bus message_type destination path interface.member
#
# destination must be a connection name or "broadcast" for a broadcast signal
send()
{
  d=""

  if [ "$3" == "broadcast" ]
  then
    if [ "$2" != "signal" ]
    then
      fatalerror "Cannot send broadcast for message type \"$2\""
    fi
  else
    d="--name=$3"
  fi

  out=$(./dbus_message --$1 --type=$2 $d $4 $5 2>&1)
  if [ $? -ne 0 ]
  then
    fatalerror "$out"
  fi
}

sendsignal()
{
  send "$bus" "signal" "$dest" "$path" "${iface}.Signal"
}

sendbroadcastsignal()
{
  send "$bus" "signal" "broadcast" "$path" "${iface}.Signal"
}

sendmethod()
{
  send "$bus" "method_call" "$dest" "$path" "${iface}.Method"
}

# parameters: bus message_type destination
#
# destination must be a connection name
sendunrequestedreply()
{
  out=$(./dbus_unrequested_reply --$1 --type=$2 --name=$3 2>&1)
  if [ $? -ne 0 ]
  then
    fatalerror "$out"
  fi
}

sendmethodreturn()
{
  sendunrequestedreply "$bus" "method_return" "$dest"
}

senderror()
{
  sendunrequestedreply "$bus" "error" "$dest"
}

compare_logs()
{
	local msg
	local rc=0

	cmp -s "$1" "$3" || rc=$?
	if [ $rc -ne 0 ] && [ "$2" == "eq" ]
	then
		msg="Log files \"$1\" and \"$3\" are different, but should be equal."
	elif [ $rc -eq 0 ] && [ "$2" == "ne" ]
	then
		msg="Log files \"$1\" and \"$3\" are the same, but should be different."
	else
		return
	fi

	echo "Error: ${testname} failed. Test '${_testdesc}' produced unexpected log contents. ${msg}"
	testfailed
}
