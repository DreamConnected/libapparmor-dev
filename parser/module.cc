/*
 *   Copyright (c) 2021
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

#include "parser.h"
#include "profile.h"
#include "module.h"

#include <iomanip>
#include <string>
#include <iostream>
#include <sstream>

void module_rule::move_conditionals(struct cond_entry *conds)
{
	struct cond_entry *cond_ent;

	list_for_each(conds, cond_ent) {
		/* for now disallow keyword 'in' (list) */
		if (!cond_ent->eq)
			yyerror("keyword \"in\" is not allowed in module rules\n");

		/* no valid conditionals atm */
		yyerror("invalid module rule conditional \"%s\"\n",
			cond_ent->name);
	}
}

module_rule::module_rule(int perms_p, struct cond_entry *conds, char *target_p):
	perms_rule_t(AA_CLASS_MODULE)
{
	if (perms_p) {
		if (perms_p & ~AA_VALID_MODULE_PERMS)
			yyerror("perms contains invalid permissions for module\n");
		perms = perms_p;
	} else {
		// default to all perms
		perms = AA_VALID_MODULE_PERMS;
	}
	target = target_p;

	move_conditionals(conds);
	free_cond_list(conds);
}

ostream &module_rule::dump(ostream &os)
{
	class_rule_t::dump(os);

	if (perms != AA_VALID_MODULE_PERMS) {
		os << " ( ";

		if (perms & AA_MAY_LOAD_DATA)
			os << "load_data ";
		if (perms & AA_MAY_LOAD_FILE)
			os << "load_file ";
		if (perms & AA_MAY_REQUEST)
			os << "request ";

		os << ")";
	}

	if (target)
		os << " " << target;

	os << ",\n";

	return os;
}


int module_rule::expand_variables(void)
{
	return expand_entry_variables(&target);
}

void module_rule::warn_once(const char *name)
{
	rule_t::warn_once(name, "module rules not enforced");
}

int module_rule::gen_policy_re(Profile &prof)
{
	std::ostringstream buffer;
	std::string buf;

	if (!features_supports_module) {
		warn_once(prof.name);
		return RULE_NOT_SUPPORTED;
	}

	buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << AA_CLASS_MODULE;

	if (target) {
		if (!convert_entry(buf, target))
			goto fail;
		buffer << buf;
	} else {
		buffer << default_match_pattern;
	}

	buf = buffer.str();
	if (perms & AA_VALID_MODULE_PERMS) {
		if (!prof.policy.rules->add_rule(buf.c_str(), rule_mode == RULE_DENY, perms,
						 audit == AUDIT_FORCE ? perms : 0,
						 dfaflags))
			goto fail;
	}
	return RULE_OK;
fail:
	return RULE_ERROR;
}
