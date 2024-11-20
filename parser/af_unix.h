/*
 *   Copyright (c) 2014
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
#ifndef __AA_AF_UNIX_H
#define __AA_AF_UNIX_H

#include "immunix.h"
#include "network.h"
#include "parser.h"
#include "profile.h"
#include "af_rule.h"

int parse_unix_perms(const char *str_mode, perm32_t *perms, int fail);

class unix_rule: public af_rule {
	void write_to_prot(std::ostringstream &buffer);
	bool write_addr(std::ostringstream &buffer, const char *addr);
	bool write_label(std::ostringstream &buffer, const char *label);
	void move_conditionals(struct cond_entry *conds);
	void move_peer_conditionals(struct cond_entry *conds);
	void downgrade_rule(Profile &prof);
public:
	char *addr;
	char *peer_addr;
	bool downgrade = true;

	unix_rule(unsigned int type_p, audit_t audit_p, rule_mode_t rule_mode_p);
	unix_rule(perm32_t perms, struct cond_entry *conds,
		  struct cond_entry *peer_conds);
	virtual ~unix_rule()
	{
		free(addr);
		free(peer_addr);
	};

	// Delete the copy constructors to prevent accidental pointer aliasing
	unix_rule(const unix_rule&) = delete;
	unix_rule& operator=(const unix_rule&) = delete;
	// TODO: write move constructors if that is desired later

	virtual bool valid_prefix(const prefixes &p, const char *&error) {
		// priority is partially supported for unix rules
		// rules that get downgraded to just network socket
		// won't support them but the fine grained do.
		if (p.owner) {
			error = "owner prefix not allowed on unix rules";
			return false;
		}
		return true;
	};
	virtual bool has_peer_conds(void) {
		return af_rule::has_peer_conds() || peer_addr;
	}

	virtual ostream &dump_local(ostream &os);
	virtual ostream &dump_peer(ostream &os);
	virtual int expand_variables(void);
	virtual int gen_policy_re(Profile &prof);

	// inherit is_mergable() from af_rule
	virtual int cmp(rule_t const &rhs) const
	{
		int res = af_rule::cmp(rhs);
		if (res)
			return res;
		unix_rule const &trhs = (rule_cast<unix_rule const &>(rhs));
		res = null_strcmp(addr, trhs.addr);
		if (res)
			return res;
		return null_strcmp(peer_addr, trhs.peer_addr);
	};

protected:
	virtual void warn_once(const char *name) override;
};

#endif /* __AA_AF_UNIX_H */
