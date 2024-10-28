/*
 *   Copyright (c) 2022
 *   Canonical, Ltd. (All rights reserved)
 *
 *   This program is free software; you can redistribute it and/or
 *   modify it under the terms of version 2 of the GNU General Public
 *   License published by the Free Software Foundation.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program; if not, contact Novell, Inc. or Canonical
 *   Ltd.
 */
#ifndef __AA_PERM_H
#define __AA_PERM_H

/* this represents permissions as used as part of the state machine in
 * the kernel.
 * It is possible this will get further mapped for compatibility with
 * older versions
 */

#include <ostream>
#include <iostream>
using std::ostream;
using std::cerr;

#include <stdint.h>
#include <sys/apparmor.h>

/* same as in immunix.h - make it so they can both be included or used alone */
#ifndef AA_MAY_EXEC
#define AA_MAY_EXEC		1
#define AA_MAY_WRITE		2
#define AA_MAY_READ		4
#define AA_MAY_APPEND		8
#endif

#ifndef AA_MAY_CREATE
// these are in apparmor.h
#define AA_MAY_CREATE		0x0010
#define AA_MAY_DELETE		0x0020
#define AA_MAY_OPEN		0x0040
#define AA_MAY_RENAME		0x0080		/* pair */

#define AA_MAY_SETATTR		0x0100		/* meta write */
#define AA_MAY_GETATTR		0x0200		/* meta read */
#define AA_MAY_SETCRED		0x0400		/* security cred/attr */
#define AA_MAY_GETCRED		0x0800

#define AA_MAY_CHMOD		0x1000		/* pair */
#define AA_MAY_CHOWN		0x2000		/* pair */
#endif
#define AA_MAY_CHGRP		0x4000		/* pair */
#ifndef AA_MAY_CREATE
#define AA_MAY_LOCK		0x8000		/* LINK_SUBSET overlaid */

#define AA_EXEC_MMAP		0x00010000
#endif
#define AA_MAY_MPROT		0x00020000	/* extend conditions */
#ifndef AA_MAY_CREATE
#define AA_MAY_LINK		0x00040000	/* pair */
#endif
#define AA_MAY_SNAPSHOT		0x00080000	/* pair */

#define AA_MAY_DELEGATE
#define AA_CONT_MATCH		0x08000000

// TODO: move into a reworked immunix.h that is dependent on perms.h
#define AA_COMPAT_CONT_MATCH	(AA_CONT_MATCH << 1)

#define AA_MAY_STACK		0x10000000
#define AA_MAY_ONEXEC		0x20000000 /* either stack or change_profile */
#define AA_MAY_CHANGE_PROFILE	0x40000000
#define AA_MAY_CHANGEHAT	0x80000000

#define AA_LINK_SUBSET		AA_MAY_LOCK	/* overlaid */


/*
 * The xindex is broken into 3 parts
 * - index - an index into either the exec name table or the variable table
 * - exec type - which determines how the executable name and index are used
 * - flags - which modify how the destination name is applied
 */
#define AA_X_INDEX_MASK		0xffffff

#define AA_X_TYPE_MASK		0x0c000000
#define AA_X_NONE		AA_INDEX_NONE
#define AA_X_NAME		0x04000000 /* use executable name px */
#define AA_X_TABLE		0x08000000 /* use a specified name ->n# */

#define AA_X_UNSAFE		0x10000000
#define AA_X_CHILD		0x20000000
#define AA_X_INHERIT		0x40000000
#define AA_X_UNCONFINED		0x80000000

typedef uint32_t perm32_t;

class aa_perms {
public:
	perm32_t allow;
	perm32_t deny;	/* explicit deny, or conflict if allow also set */

	perm32_t subtree;	/* allow perm on full subtree only when allow is set */
	perm32_t cond;	/* set only when ~allow and ~deny */

	perm32_t kill;	/* set only when ~allow | deny */
	perm32_t complain;	/* accumulates only used when ~allow & ~deny */
	perm32_t prompt;	/* accumulates only used when ~allow & ~deny */

	perm32_t audit;	/* set only when allow is set */
	perm32_t quiet;	/* set only when ~allow | deny */
	perm32_t hide;	/* set only when  ~allow | deny */


	uint32_t xindex;
	uint32_t tag;	/* tag string index, if present */
	uint32_t label;	/* label string index, if present */

	void dump_header(ostream &os)
	{
		os << "(allow/deny/prompt//audit/quiet//xindex)\n";
	}

	void dump(ostream &os)
	{
		os << std::hex << "(0x" << allow << "/0x" << deny << "/0x"
		   << prompt << "//0x" << audit << "/0x" << quiet
		   << std::dec << "//";
		if (xindex & AA_X_UNSAFE)
			os << "unsafe ";
		if (xindex & AA_X_TYPE_MASK) {
			if (xindex & AA_X_CHILD)
				os << "c";
			else
				os << "p";
		}
		if (xindex & AA_X_INHERIT)
			os << "i";
		if (xindex & AA_X_UNCONFINED)
			os << "u";
		os << (xindex & AA_X_INDEX_MASK);
		os << ")";
	}

};

#endif /* __AA_PERM_H */
