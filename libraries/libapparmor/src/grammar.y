/*
 * Copyright (c) 1999-2008 NOVELL (All rights reserved)
 * Copyright (c) 2010, Canonical, Ltd.
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

/* aalogparse_error now requires visibility of the aa_log_record type
 * Also include in a %code requires block to add it to the header
 */
%code requires{
	#include <aalogparse.h>
}

%{

#include <string.h>
#include <aalogparse.h>
#include "parser.h"
#include "grammar.h"
#include "scanner.h"

#ifndef unused_
#define unused_ __attribute__ ((unused))
#endif
#if (YYDEBUG != 0)
#define debug_unused_ /* nothing */
#else
#define debug_unused_ unused_
#endif

/* Since we're a library, on any errors we don't want to print out any
 * error messages. We should probably add a debug interface that does
 * emit messages when asked for. */
void aalogparse_error(unused_ void *scanner, aa_log_record *ret_record, debug_unused_ char const *s)
{
#if (YYDEBUG != 0)
	printf("ERROR: %s\n", s);
#endif
	ret_record->event = AA_RECORD_INVALID;
}

struct aa_type_table {
	unsigned int audit_type;
	aa_record_event_type event;
};

static struct aa_type_table aa_type_table[] = {
	{AUDIT_APPARMOR_AUDIT,   AA_RECORD_AUDIT},
	{AUDIT_APPARMOR_ALLOWED, AA_RECORD_ALLOWED},
	{AUDIT_APPARMOR_DENIED,  AA_RECORD_DENIED},
	{AUDIT_APPARMOR_HINT,    AA_RECORD_HINT},
	{AUDIT_APPARMOR_STATUS,  AA_RECORD_STATUS},
	{AUDIT_APPARMOR_ERROR,   AA_RECORD_ERROR},
	{0,                      AA_RECORD_INVALID},
};

aa_record_event_type lookup_aa_event(unsigned int type)
{
	int i;

	for (i = 0; aa_type_table[i].audit_type != 0; i++)
		if (type == aa_type_table[i].audit_type)
			break;

	return aa_type_table[i].event;
}


%}

%defines
/* uncomment for debugging
%define parse.error verbose
%define parse.trace
*/

%define api.pure full
%lex-param{void *scanner}
%parse-param{void *scanner}
%parse-param{aa_log_record *ret_record}

%union
{
	char	*t_str;
	long	t_long;
}

%type <t_str> safe_string protocol
%token <t_long> TOK_DIGITS TOK_TYPE_UNKNOWN
%token <t_str> TOK_QUOTED_STRING TOK_ID TOK_MODE TOK_DMESG_STAMP
%token <t_str> TOK_AUDIT_DIGITS TOK_DATE_MONTH TOK_DATE TOK_TIME
%token <t_str> TOK_HEXSTRING TOK_TYPE_OTHER TOK_MSG_REST
%token <t_str> TOK_IP_ADDR

%token TOK_EQUALS
%token TOK_COLON
%token TOK_MINUS
%token TOK_OPEN_PAREN
%token TOK_CLOSE_PAREN
%token TOK_PERIOD
%token TOK_QUESTION_MARK
%token TOK_SINGLE_QUOTE
%token TOK_NONE

%token TOK_TYPE_REJECT
%token TOK_TYPE_AUDIT
%token TOK_TYPE_COMPLAIN
%token TOK_TYPE_HINT
%token TOK_TYPE_STATUS
%token TOK_TYPE_ERROR
%token TOK_TYPE_AA_REJECT
%token TOK_TYPE_AA_AUDIT
%token TOK_TYPE_AA_COMPLAIN
%token TOK_TYPE_AA_HINT
%token TOK_TYPE_AA_STATUS
%token TOK_TYPE_AA_ERROR
%token TOK_TYPE_LSM_AVC
%token TOK_TYPE_USER_AVC

%token TOK_KEY_APPARMOR
%token TOK_KEY_TYPE
%token TOK_KEY_MSG
%token TOK_KEY_OPERATION
%token TOK_KEY_NAME
%token TOK_KEY_NAME2
%token TOK_KEY_MASK
%token TOK_KEY_DENIED_MASK
%token TOK_KEY_REQUESTED_MASK
%token TOK_KEY_ATTRIBUTE
%token TOK_KEY_TASK
%token TOK_KEY_PARENT
%token TOK_KEY_MAGIC_TOKEN
%token TOK_KEY_INFO
%token TOK_KEY_PEER_INFO
%token TOK_KEY_PID
%token TOK_KEY_PEER_PID
%token TOK_KEY_PROFILE
%token TOK_KEY_PEER_PROFILE
%token TOK_KEY_LABEL
%token TOK_KEY_PEER_LABEL
%token TOK_KEY_PEER
%token TOK_AUDIT
%token TOK_KEY_FAMILY
%token TOK_KEY_SOCK_TYPE
%token TOK_KEY_PROTOCOL
%token TOK_KEY_NAMESPACE
%token TOK_KEY_ERROR
%token TOK_KEY_FSUID
%token TOK_KEY_FSUID_UPPER
%token TOK_KEY_OUID
%token TOK_KEY_OUID_UPPER
%token TOK_KEY_UID
%token TOK_KEY_AUID
%token TOK_KEY_SAUID
%token TOK_KEY_SES
%token TOK_KEY_HOSTNAME
%token TOK_KEY_ADDR
%token TOK_KEY_TERMINAL
%token TOK_KEY_EXE
%token TOK_KEY_COMM
%token TOK_KEY_CAPABILITY
%token TOK_KEY_CAPNAME
%token TOK_KEY_OFFSET
%token TOK_KEY_TARGET
%token TOK_KEY_LADDR
%token TOK_KEY_FADDR
%token TOK_KEY_LPORT
%token TOK_KEY_FPORT
%token TOK_KEY_BUS
%token TOK_KEY_PATH
%token TOK_KEY_INTERFACE
%token TOK_KEY_MEMBER
%token TOK_KEY_SIGNAL
%token TOK_KEY_FSTYPE
%token TOK_KEY_FLAGS
%token TOK_KEY_SRCNAME
%token TOK_KEY_UNIX_PEER_ADDR
%token TOK_KEY_EXECPATH
%token TOK_KEY_CLASS

%token TOK_SOCKLOGD_KERNEL
%token TOK_SYSLOG_KERNEL
%token TOK_SYSLOG_USER

%destructor { free($$); } TOK_QUOTED_STRING TOK_ID TOK_MODE TOK_DMESG_STAMP
%destructor { free($$); } TOK_AUDIT_DIGITS TOK_DATE_MONTH TOK_DATE TOK_TIME
%destructor { free($$); } TOK_HEXSTRING TOK_TYPE_OTHER TOK_MSG_REST
%destructor { free($$); } TOK_IP_ADDR

%%

log_message: audit_type
	| dmesg_type
	| syslog_type
	| audit_dispatch
	;

audit_type: TOK_KEY_TYPE TOK_EQUALS type_syntax ;

type_syntax: new_syntax { ret_record->version = AA_RECORD_SYNTAX_V2; }
	| other_audit
	;

new_syntax:
	  TOK_TYPE_AA_REJECT audit_msg key_list { ret_record->event = AA_RECORD_DENIED; }
	| TOK_TYPE_AA_AUDIT audit_msg key_list { ret_record->event = AA_RECORD_AUDIT; }
	| TOK_TYPE_AA_COMPLAIN audit_msg key_list { ret_record->event = AA_RECORD_ALLOWED; }
	| TOK_TYPE_AA_HINT audit_msg key_list { ret_record->event = AA_RECORD_HINT; }
	| TOK_TYPE_AA_STATUS audit_msg key_list { ret_record->event = AA_RECORD_STATUS; }
	| TOK_TYPE_AA_ERROR audit_msg key_list { ret_record->event = AA_RECORD_ERROR; }
	| TOK_TYPE_UNKNOWN audit_msg key_list { ret_record->event = lookup_aa_event($1); }
	| TOK_TYPE_LSM_AVC audit_msg key_list
	| TOK_TYPE_USER_AVC audit_user_msg
	;

other_audit: TOK_TYPE_OTHER audit_msg TOK_MSG_REST
	{
		ret_record->operation = $1;
		ret_record->event = AA_RECORD_INVALID;
		ret_record->info = $3;
	}
	;

dmesg_type: TOK_DMESG_STAMP TOK_AUDIT TOK_COLON key_type audit_id key_list
	{ ret_record->version = AA_RECORD_SYNTAX_V2; free($1); }
	;

syslog_id: TOK_ID TOK_SYSLOG_KERNEL { free($1); }
	| TOK_SOCKLOGD_KERNEL { }
	;

syslog_type:
	  syslog_date syslog_id audit_id key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; }
	| syslog_date syslog_id key_type audit_id key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; }
	| syslog_date syslog_id TOK_DMESG_STAMP audit_id key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; free($3); }
	| syslog_date syslog_id TOK_DMESG_STAMP key_type audit_id key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; free($3); }
	/* needs update: hard newline in handling multiline log messages */
	| syslog_date syslog_id TOK_DMESG_STAMP TOK_AUDIT TOK_COLON key_type audit_id audit_user_msg_partial_tail
	  { ret_record->version = AA_RECORD_SYNTAX_V2; free($3); }
	| syslog_date syslog_id TOK_DMESG_STAMP TOK_AUDIT TOK_COLON key_type audit_id audit_user_msg_tail
	  { ret_record->version = AA_RECORD_SYNTAX_V2; free($3); }
	| syslog_date syslog_id TOK_DMESG_STAMP TOK_AUDIT TOK_COLON key_type audit_id key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; free($3); }
	| syslog_date syslog_id TOK_AUDIT TOK_COLON key_type audit_id key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; }
	| syslog_date TOK_ID TOK_SYSLOG_USER key_list
	  { ret_record->version = AA_RECORD_SYNTAX_V2; free($2); }
	;

/* when audit dispatches a message it doesn't prepend the audit type string */
audit_dispatch:
	audit_msg key_list { ret_record->version = AA_RECORD_SYNTAX_V2; }
	;

audit_msg: TOK_KEY_MSG TOK_EQUALS audit_id
	;

audit_user_msg_partial_tail: ignored_pid ignored_uid ignored_auid ignored_ses TOK_KEY_MSG TOK_EQUALS TOK_SINGLE_QUOTE key_list
	;

audit_user_msg_tail: audit_user_msg_partial_tail TOK_SINGLE_QUOTE
	;

audit_user_msg: TOK_KEY_MSG TOK_EQUALS audit_id audit_user_msg_tail
	;

audit_id: TOK_AUDIT TOK_OPEN_PAREN TOK_AUDIT_DIGITS TOK_PERIOD TOK_AUDIT_DIGITS TOK_COLON TOK_AUDIT_DIGITS TOK_CLOSE_PAREN TOK_COLON
	{
		if (!asprintf(&ret_record->audit_id, "%s.%s:%s", $3, $5, $7)) {
			yyerror(scanner, ret_record, YY_("Out of memory"));
		}
		ret_record->epoch = atol($3);
		ret_record->audit_sub_id = atoi($7);
		free($3);
		free($5);
		free($7);
	} ;

syslog_date: TOK_DATE_MONTH TOK_DIGITS TOK_TIME
		{ free($1); free($3); /* do nothing */ }
	| TOK_DATE TOK_TIME
		{ free($1); free($2); /* do nothing */ }
	;

key_list: key
	| key_list key
	;

key: TOK_KEY_OPERATION TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->operation = $3;}
	| TOK_KEY_NAME TOK_EQUALS safe_string
	{ ret_record->name = $3;}
	| TOK_KEY_NAMESPACE TOK_EQUALS safe_string
	{ ret_record->aa_namespace = $3;}
	| TOK_KEY_NAME2 TOK_EQUALS safe_string
	{ ret_record->name2 = $3;}
	| TOK_KEY_MASK TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->denied_mask = $3;}
	| TOK_KEY_DENIED_MASK TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->denied_mask = $3;}
	| TOK_KEY_REQUESTED_MASK TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->requested_mask = $3;}
	| TOK_KEY_ATTRIBUTE TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->attribute = $3;}
	| TOK_KEY_TASK TOK_EQUALS TOK_DIGITS
	{ ret_record->task = $3;}
	| TOK_KEY_PARENT TOK_EQUALS TOK_DIGITS
	{ ret_record->parent = $3;}
	| TOK_KEY_MAGIC_TOKEN TOK_EQUALS TOK_DIGITS
	{ ret_record->magic_token = $3;}
	| TOK_KEY_INFO TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->info = $3;}
	| TOK_KEY_PEER_INFO TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->peer_info = $3;}
	| TOK_KEY_PEER TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->peer = $3;}
	| key_pid
	| key_peer_pid
	| TOK_KEY_PROFILE TOK_EQUALS safe_string
	{ ret_record->profile = $3;}
	| TOK_KEY_PEER_PROFILE TOK_EQUALS safe_string
	{ ret_record->peer_profile = $3;}
	| TOK_KEY_LABEL TOK_EQUALS safe_string
	{ ret_record->profile = $3;}
	| TOK_KEY_PEER_LABEL TOK_EQUALS safe_string
	{ ret_record->peer_profile = $3;}
	| TOK_KEY_FAMILY TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->net_family = $3;}
	| TOK_KEY_SOCK_TYPE TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->net_sock_type = $3;}
	| TOK_KEY_PROTOCOL TOK_EQUALS protocol
	{ ret_record->net_protocol = $3;}
	| TOK_KEY_TYPE TOK_EQUALS TOK_DIGITS
	{ ret_record->event = lookup_aa_event($3);}
	| TOK_KEY_ERROR TOK_EQUALS TOK_DIGITS
	{ ret_record->error_code = $3;}
	| TOK_KEY_ERROR TOK_EQUALS TOK_MINUS TOK_DIGITS
	{ ret_record->error_code = $4;}
	| TOK_KEY_FSUID TOK_EQUALS TOK_DIGITS
	{ ret_record->fsuid = $3;}
	| TOK_KEY_OUID TOK_EQUALS TOK_DIGITS
	{ ret_record->ouid = $3;}
	| TOK_KEY_ADDR TOK_EQUALS TOK_QUESTION_MARK
	| TOK_KEY_ADDR TOK_EQUALS TOK_NONE
	| TOK_KEY_ADDR TOK_EQUALS safe_string
	{ ret_record->net_addr = $3; }
	| TOK_KEY_UNIX_PEER_ADDR TOK_EQUALS TOK_NONE
	| TOK_KEY_UNIX_PEER_ADDR TOK_EQUALS safe_string
	{ ret_record->peer_addr = $3; }
	| TOK_KEY_FSUID_UPPER TOK_EQUALS TOK_QUOTED_STRING
	{ free($3);} /* Ignore - fsuid username */
	| TOK_KEY_OUID_UPPER TOK_EQUALS TOK_QUOTED_STRING
	{ free($3);} /* Ignore - ouid username */
	| TOK_KEY_SAUID TOK_EQUALS TOK_DIGITS
	{ /* Ignore - Source audit ID from user AVC messages */ }
	| TOK_KEY_HOSTNAME TOK_EQUALS safe_string
	{ free($3); /* Ignore - hostname from user AVC messages */ }
	| TOK_KEY_HOSTNAME TOK_EQUALS TOK_QUESTION_MARK
	| TOK_KEY_TERMINAL TOK_EQUALS TOK_QUESTION_MARK
	| TOK_KEY_TERMINAL TOK_EQUALS safe_string
	{ free($3); /* Ignore - TTY from user AVC messages */ }
	| TOK_KEY_EXE TOK_EQUALS safe_string
	{ /* Free existing arrays because exe= and comm= maps to the same
	     aa_log_record member */
	  free(ret_record->comm);
	  ret_record->comm = $3;
	}
	| TOK_KEY_COMM TOK_EQUALS safe_string
	{ /* Free existing arrays because exe= and comm= maps to the same
	     aa_log_record member */
	  free(ret_record->comm);
	  ret_record->comm = $3;
	}
	| TOK_KEY_APPARMOR TOK_EQUALS apparmor_event
	| TOK_KEY_CAPABILITY TOK_EQUALS TOK_DIGITS
	{ /* need to reverse map number to string, need to figure out
	   * how to get auto generation of reverse mapping table into
	   * autotools Makefile.  For now just drop assuming capname is
	   * present which it should be with current kernels */
	}
	| TOK_KEY_CAPNAME TOK_EQUALS TOK_QUOTED_STRING
	{ /* capname used to be reported in name */
	  ret_record->name = $3;
	}
	| TOK_KEY_OFFSET TOK_EQUALS TOK_DIGITS
	{ /* offset is used for reporting where an error occurred unpacking
	   * loaded policy.  We can just drop this currently
	   */
	}
	| TOK_KEY_TARGET TOK_EQUALS safe_string
	{ /* target was always name2 in the past */
	  ret_record->name2 = $3;
	}
	| TOK_KEY_LADDR TOK_EQUALS TOK_IP_ADDR
	{ ret_record->net_local_addr = $3;}
	| TOK_KEY_FADDR TOK_EQUALS TOK_IP_ADDR
	{ ret_record->net_foreign_addr = $3;}
	| TOK_KEY_LPORT TOK_EQUALS TOK_DIGITS
	{ ret_record->net_local_port = $3;}
	| TOK_KEY_FPORT TOK_EQUALS TOK_DIGITS
	{ ret_record->net_foreign_port = $3;}
	| TOK_KEY_BUS TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->dbus_bus = $3; }
	| TOK_KEY_PATH TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->dbus_path = $3; }
	| TOK_KEY_INTERFACE TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->dbus_interface = $3; }
	| TOK_KEY_MEMBER TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->dbus_member = $3; }
	| TOK_KEY_SIGNAL TOK_EQUALS TOK_ID
	{ ret_record->signal = $3; }
	| TOK_KEY_FSTYPE TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->fs_type = $3; }
	| TOK_KEY_FLAGS TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->flags = $3; }
	| TOK_KEY_SRCNAME TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->src_name = $3; }
	| TOK_KEY_EXECPATH TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->execpath = $3; }
	| TOK_MSG_REST
	{
		ret_record->event = AA_RECORD_INVALID;
		ret_record->info = $1;
	}
	| TOK_KEY_CLASS TOK_EQUALS TOK_QUOTED_STRING
	{ ret_record->rule_class = $3; }
	;

apparmor_event:
	  TOK_TYPE_REJECT	{ ret_record->event = AA_RECORD_DENIED; }
	| TOK_TYPE_AUDIT	{ ret_record->event = AA_RECORD_AUDIT; }
	| TOK_TYPE_COMPLAIN	{ ret_record->event = AA_RECORD_ALLOWED; }
	| TOK_TYPE_HINT		{ ret_record->event = AA_RECORD_HINT; }
	| TOK_TYPE_STATUS	{ ret_record->event = AA_RECORD_STATUS; }
	| TOK_TYPE_ERROR	{ ret_record->event = AA_RECORD_ERROR; }
	;

key_pid: TOK_KEY_PID TOK_EQUALS TOK_DIGITS { ret_record->pid = $3; }
	;

key_peer_pid: TOK_KEY_PEER_PID TOK_EQUALS TOK_DIGITS { ret_record->peer_pid = $3; }
	;

ignored_pid:  TOK_KEY_PID  TOK_EQUALS TOK_DIGITS { /* DROP */ }
ignored_uid:  TOK_KEY_UID  TOK_EQUALS TOK_DIGITS { /* DROP */ }
ignored_auid: TOK_KEY_AUID TOK_EQUALS TOK_DIGITS { /* DROP */ }
ignored_ses:  TOK_KEY_SES  TOK_EQUALS TOK_DIGITS { /* DROP */ }

key_type: TOK_KEY_TYPE TOK_EQUALS TOK_DIGITS { ret_record->event = lookup_aa_event($3); }
	;

safe_string: TOK_QUOTED_STRING
	| TOK_HEXSTRING
	;

protocol: TOK_QUOTED_STRING
	| TOK_DIGITS
	{ /* FIXME: this should probably convert back to a string proto name */
	  $$ = ipproto_to_string($1);
	}
	;
%%
