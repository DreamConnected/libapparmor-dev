/*
 *   Copyright (c) 2023
 *   Canonical Ltd. (All rights reserved)
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
 *   along with this program; if not, contact Canonical Ltd.
 */

#include "common_optarg.h"
#include "parser.h"
#include "profile.h"
#include "io_uring.h"

#include <iomanip>
#include <string>
#include <iostream>
#include <sstream>

void io_uring_rule::move_conditionals(struct cond_entry *conds)
{
	struct cond_entry *cond_ent;

	list_for_each(conds, cond_ent) {
		/* disallow keyword 'in' (list) */
		if (!cond_ent->eq)
			yyerror("keyword \"in\" is not allowed in io_uring rules\n");

		if (cond_ent->vals->size() > 1)
			yyerror("io_uring conditional \"%s\" only supports a single value\n",
				cond_ent->name);

		if (strcmp(cond_ent->name, "label") == 0) {
			move_conditional_value("io_uring", &label, cond_ent);
		} else {
			yyerror("invalid io_uring conditional \"%s\"\n",
				cond_ent->name);
		}
	}
}

io_uring_rule::io_uring_rule(perm32_t perms_p, struct cond_entry *conds, struct cond_entry *ring_conds):
	perms_rule_t(AA_CLASS_IO_URING), label(NULL)
{
	if (perms_p) {
		if (perms_p & ~AA_VALID_IO_URING_PERMS) {
			yyerror("perms contains invalid permissions for io_uring\n");
		}
		perms = perms_p;

	} else {
		/* default to all perms */
		perms = AA_VALID_IO_URING_PERMS;
	}
	move_conditionals(conds);
	move_conditionals(ring_conds);
	free_cond_list(conds);
	free_cond_list(ring_conds);
}

ostream &io_uring_rule::dump(ostream &os)
{
	class_rule_t::dump(os);

	if (perms != AA_VALID_IO_URING_PERMS) {
		os << " ( ";

		if (perms & AA_IO_URING_OVERRIDE_CREDS)
			os << "override_creds ";
		if (perms & AA_IO_URING_SQPOLL)
			os << " sqpoll ";

		os << ")";
	}

	if (label)
		os << " label=" << label;

	os << ",\n";

	return os;
}


int io_uring_rule::expand_variables(void)
{
	return 0;
}

void io_uring_rule::warn_once(const char *name)
{
	rule_t::warn_once(name, "io_uring rules not enforced");
}

int io_uring_rule::gen_policy_re(Profile &prof)
{
	std::ostringstream buffer;
	std::string buf, labelbuf;

	if (!features_supports_io_uring) {
		warn_once(prof.name);
		return RULE_NOT_SUPPORTED;
	}

	buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << AA_CLASS_IO_URING;
	buf = buffer.str();

	if (label) {
		if (!convert_entry(labelbuf, label))
			goto fail;
		buffer << labelbuf;
	} else {
		buffer << default_match_pattern;
	}

	if (perms & AA_VALID_IO_URING_PERMS) {
		if (!prof.policy.rules->add_rule(buf.c_str(), priority,
					rule_mode, perms,
					audit == AUDIT_FORCE ? perms : 0,
					parseopts))
			goto fail;
		/* add a mediates_io_uring rule for every rule added. It
		 * needs to be the same priority
		 */
		if (!prof.policy.rules->add_rule(buf.c_str(), priority,
					RULE_ALLOW, AA_MAY_READ, 0,
					parseopts))
			goto fail;

		if (perms & AA_IO_URING_OVERRIDE_CREDS) {
			buf = buffer.str(); /* update buf to have label */
			if (!prof.policy.rules->add_rule(buf.c_str(),
					priority, rule_mode,
					perms, audit == AUDIT_FORCE ? perms : 0,
					parseopts))
				goto fail;
		}

	}
	return RULE_OK;
fail:
	return RULE_ERROR;
}
