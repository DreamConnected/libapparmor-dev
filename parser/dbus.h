/*
 *   Copyright (c) 2013
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

#ifndef __AA_DBUS_H
#define __AA_DBUS_H

#include "parser.h"
#include "rule.h"
#include "profile.h"

extern int parse_dbus_perms(const char *str_mode, perms_t *mode, int fail);

class dbus_rule: public perms_rule_t {
	void move_conditionals(struct cond_entry *conds);
public:
	char *bus;
	/**
	 * Be careful! ->name can be the subject or the peer name, depending on
	 * whether the rule is a bind rule or a send/receive rule. See the
	 * comments in new_dbus_entry() for details.
	 */
	char *name;
	char *peer_label;
	char *path;
	char *interface;
	char *member;

	dbus_rule(perms_t perms_p, struct cond_entry *conds,
		  struct cond_entry *peer_conds);
	virtual ~dbus_rule() {
		free(bus);
		free(name);
		free(peer_label);
		free(path);
		free(interface);
		free(member);
	};
	virtual bool valid_prefix(const prefixes &p, const char *&error) {
		if (p.owner) {
			error = "owner prefix not allowed on dbus rules";
			return false;
		}
		return true;
	};

	virtual ostream &dump(ostream &os);
	virtual int expand_variables(void);
	virtual int gen_policy_re(Profile &prof);

	virtual bool is_mergeable(void) { return true; }
	virtual int cmp(rule_t const &rhs) const
	{
		/* use class_rule_t instead of perms_rule_t to merge perms */
		int res = class_rule_t::cmp(rhs);
		if (res)
			return res;
		dbus_rule const &trhs = (rule_cast<dbus_rule const &>(rhs));
		res = null_strcmp(bus, trhs.bus);
		if (res)
			return res;
		res = null_strcmp(name, trhs.name);
		if (res)
			return res;
		res = null_strcmp(peer_label, trhs.peer_label);
		if (res)
			return res;
		res = null_strcmp(path, trhs.path);
		if (res)
			return res;
		res = null_strcmp(interface, trhs.interface);
		if (res)
			return res;
		return null_strcmp(member, trhs.member);
	};


protected:
	virtual void warn_once(const char *name) override;
};

#endif /* __AA_DBUS_H */
