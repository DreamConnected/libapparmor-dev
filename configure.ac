#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

# Set version so we need to edit in one place (i.e., here)
#
m4_define([__apparmor_version], m4_sinclude(common/Version))
m4_define([__aalen], decr(len(__apparmor_version)))
m4_define([apparmor_version], m4_substr(__apparmor_version, 0, __aalen))

AC_PREREQ(2.69)
AC_INIT([apparmor], apparmor_version)
AC_CONFIG_SRCDIR([binutils/aa_enabled.c])
# AC_CONFIG_HEADERS([config.h])

# Since nesting packages, ensure automake looks for helper scripts in
# the current directory
AC_CONFIG_AUX_DIR([.])
AM_INIT_AUTOMAKE

# Checks for programs.
# currently ISO standard C (C99)
AC_PROG_CC_STDC

# Checks for libraries.

# Checks for header files.
AC_CHECK_HEADERS([libintl.h  unistd.h])

AC_CONFIG_FILES([
	Makefile
])
AC_CONFIG_SUBDIRS([libraries/libapparmor])
AC_OUTPUT
