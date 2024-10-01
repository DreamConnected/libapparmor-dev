/*
 * Copyright (c) 1999-2008 NOVELL (All rights reserved)
 * Copyright 2009-2010 Canonical Ltd.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of version 2.1 of the GNU Lesser General
 * Public License published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */


#ifndef __LIBAALOGPARSE_H_
#define __LIBAALOGPARSE_H_

#ifdef __cplusplus
extern "C" {
#endif

#define AA_RECORD_EXEC_MMAP	1
#define AA_RECORD_READ		2
#define AA_RECORD_WRITE		4
#define AA_RECORD_EXEC		8
#define AA_RECORD_LINK		16

/**
 * Enum representing which syntax version the log entry used.
 * Support for V1 parsing was completely removed in 2011 and that enum entry
 * is only still there for API compatibility reasons.
 */
typedef enum
{
	AA_RECORD_SYNTAX_V1,
	AA_RECORD_SYNTAX_V2,
	AA_RECORD_SYNTAX_UNKNOWN
} aa_record_syntax_version;

typedef enum
{
	AA_RECORD_INVALID,	/* Default event type */
	AA_RECORD_ERROR,	/* Internal AA error */
	AA_RECORD_AUDIT,	/* Audited event */
	AA_RECORD_ALLOWED,	/* Complain mode event */
	AA_RECORD_DENIED,	/* Denied access event */
	AA_RECORD_HINT,		/* Process tracking info */
	AA_RECORD_STATUS	/* Configuration change */
} aa_record_event_type;

/*
 * Use this preprocessor dance to maintain backcompat for field names
 * This will break C code that used the C++ reserved keywords "namespace"
 * and "class" as identifiers, but this is bad practice anyways, and we
 * hope that we are the only ones in a given C file that messed up this way
 *
 * TODO: document this in a man page for aalogparse?
 */
#if defined(SWIG) && defined(__cplusplus)
#error "SWIG and __cplusplus are defined together"
#elif !defined(SWIG) && !defined(__cplusplus)
/* Use SWIG's %rename feature to preserve backcompat */
#define class rule_class
#define namespace aa_namespace
#endif

typedef struct aa_log_record
{
	aa_record_syntax_version version;
	aa_record_event_type event;	/* Event type */
	unsigned long pid;		/* PID of the program logging the message */
	unsigned long peer_pid;
	unsigned long task;
	unsigned long magic_token;
	long epoch;			/* example: 12345679 */
	unsigned int audit_sub_id;	/* example: 12 */

	int bitmask;			/* Bitmask containing "r" "w" "x" etc */
	char *audit_id;			/* example: 12345679.1234:12 */
	char *operation;		/* "Exec" "Ptrace", etc. */
	char *denied_mask;		/* "r", "w", etc. */
	char *requested_mask;
	unsigned long fsuid;		/* fsuid of task - if logged */
	unsigned long ouid;		/* ouid of task - if logged */
	char *profile;			/* The name of the profile */
	char *peer_profile;
	char *comm;			/* Command that triggered msg */
	char *name;
	char *name2;
	char *aa_namespace;
	char *attribute;
	unsigned long parent;	
	char *info;
	char *peer_info;
	int error_code;			/* error_code returned if logged */
	char *active_hat;
	char *net_family;
	char *net_protocol;
	char *net_sock_type;
	char *net_local_addr;
	unsigned long net_local_port;
	char *net_foreign_addr;
	unsigned long net_foreign_port;

	char *dbus_bus;
	char *dbus_path;
	char *dbus_interface;
	char *dbus_member;
	char *signal;			/* signal name */
	char *peer;

	/* mount et al specific bits */
	char *fs_type;
	char *flags;
	char *src_name;

	char *rule_class;

	char *net_addr;
	char *peer_addr;
	char *execpath;
} aa_log_record;

/**
 * Parses a single log record string and returns a pointer to the parsed
 * data.  It is the calling program's responsibility to free that struct
 * with free_record();
 * @param[in] Record to parse.
 * @return Parsed data.
 */
aa_log_record *
parse_record(const char *str);

/**
 * Frees all struct data.
 * @param[in] Data to free.
 */
void
free_record(aa_log_record *record);

#ifdef __cplusplus
}
#endif

#endif

