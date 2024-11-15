/*
 *   Copyright (c) 2014
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

#ifndef __AA_SIGNAL_H
#define __AA_SIGNAL_H

#include "parser.h"
#include "rule.h"
#include "profile.h"


#define AA_MAY_SEND			(1 << 1)
#define AA_MAY_RECEIVE			(1 << 2)
#define AA_VALID_SIGNAL_PERMS		(AA_MAY_SEND | AA_MAY_RECEIVE)


typedef set<int> Signals;

int find_signal_mapping(const char *sig);
int parse_signal_perms(const char *str_perms, perm32_t *perms, int fail);

class signal_rule: public perms_rule_t {
	void extract_sigs(value_list *list);
	void move_conditionals(struct cond_entry *conds);
public:
	Signals signals;
	char *peer_label;

	signal_rule(perm32_t perms, struct cond_entry *conds);
	virtual ~signal_rule() {
		signals.clear();
		free(peer_label);
	};
	virtual bool valid_prefix(const prefixes &p, const char *&error) {
		if (p.owner != OWNER_UNSPECIFIED) {
			error = "owner prefix not allowed on signal rules";
			return false;
		}
		return true;
	};

	virtual ostream &dump(ostream &os);
	virtual int expand_variables(void);
	virtual int gen_policy_re(Profile &prof);

	virtual bool is_mergeable(void) { return true; }
	virtual int cmp(rule_t const &rhs) const;

protected:
	virtual void warn_once(const char *name) override;
};

#endif /* __AA_SIGNAL_H */
