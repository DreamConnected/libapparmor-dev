# ----------------------------------------------------------------------
#    Copyright (c) 2004, 2005 NOVELL (All rights reserved)
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of version 2 of the GNU General Public
#    License published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, contact Novell, Inc.
# ----------------------------------------------------------------------
all:

# As translations get added, they will automatically be included, unless
# the lang is explicitly added to DISABLED_LANGS; e.g. DISABLED_LANGS=en es

DISABLED_LANGS=
COMMONDIR=../../common

include $(COMMONDIR)/Make-po.rules

XGETTEXT_ARGS+=--language=perl --language=python

=head1 BUGS

If you find any bugs, please report them at
L<https://bugs.launchpad.net/apparmor/+filebug>.

=head1 SEE ALSO

apparmor(7), apparmor.d(5), and L<https://wiki.apparmor.net>.

=cut
