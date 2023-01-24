/tmp/apparmor/tests/regression/apparmor/dbus_message {
  dbus send bus=session path=/org/freedesktop/DBus interface=org.freedesktop.DBus member=Hello peer=(label=unconfined),

}
