# ------------------------------------------------------------------
#
#    Copyright (C) 2021 SUSE LLC
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of version 2 of the GNU General Public
#    License published by the Free Software Foundation.
#
# ------------------------------------------------------------------
# vim: ft=apparmor

abi <abi/3.0>,

include <tunables/global>
include <tunables/dovecot>

profile dovecot-decode2text.sh /usr/lib/dovecot/decode2text.sh {
  include <abstractions/base>
  include <abstractions/dovecot-common>

  /usr/lib/dovecot/decode2text.sh rm,

  # Site-specific additions and overrides. See local/README for details.
  include if exists <local/usr.lib.dovecot.decode2text.sh>
  include if exists <local/dovecot-decode2text.sh>
}
