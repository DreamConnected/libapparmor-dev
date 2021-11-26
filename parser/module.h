/*
 *   Copyright (c) 2021
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
 *   along with this program; if not, contact Novell, Inc. or Canonical
 *   Ltd.
 */
#ifndef __AA_MODULE_H
#define __AA_MODULE_H

#include "immunix.h"
#include "parser.h"

#define AA_MAY_LOAD_DATA	AA_MAY_WRITE
#define AA_MAY_LOAD_FILE	0x10		/* MAY_CREATE in new encoding */
#define AA_MAY_REQUEST		AA_MAY_APPEND
#define AA_VALID_MODULE_PERMS (AA_MAY_LOAD_DATA | AA_MAY_LOAD_FILE | AA_MAY_REQUEST)

class module_rule: public perms_rule_t {
	void move_conditionals(struct cond_entry *conds);
public:
	char *target;

	module_rule(int mode, struct cond_entry *conds, char *target);
	virtual ~module_rule()
	{
		free(target);
	};

	virtual bool valid_prefix(const prefixes &p, const char *&error) {
		if (p.owner) {
			error = _("owner prefix not allowed on userns rules");
			return false;
		}
		return true;
	};
	virtual ostream &dump(ostream &os);
	virtual int expand_variables(void);
	virtual int gen_policy_re(Profile &prof);

protected:
	virtual void warn_once(const char *name) override;
};

#endif /* __AA_MODULE_H */
