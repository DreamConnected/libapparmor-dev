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
#ifndef __AA_AF_RULE_H
#define __AA_AF_RULE_H

#include "immunix.h"
#include "network.h"
#include "parser.h"
#include "profile.h"

#include "rule.h"

#define AF_ANY -1

enum cond_side { local_cond, peer_cond, either_cond };

struct supported_cond {
	const char *name;
	bool supported;
	bool in;
	bool multivalue;
	enum cond_side side ;
};

class af_rule: public perms_rule_t {
public:
	int af;
	char *sock_type;
	int sock_type_n;
	char *proto;
	int proto_n;
	char *label;
	char *peer_label;

	af_rule(int f):
		perms_rule_t(AA_CLASS_NET),
		af(f), sock_type(NULL),
		sock_type_n(-1), proto(NULL), proto_n(0), label(NULL),
		peer_label(NULL) { }

	virtual ~af_rule()
	{
		free(sock_type);
		free(proto);
		free(label);
		free(peer_label);
	};

	// Delete the copy constructors to prevent accidental pointer aliasing
	af_rule(const af_rule&) = delete;
	af_rule& operator=(const af_rule&) = delete;
	// TODO: write move constructors if that is desired later

	const char *af_name(void) {
		if (af != AF_ANY)
			return net_find_af_name(af);
		return "*";
	}
	bool cond_check(struct supported_cond *cond, struct cond_entry *ent,
			bool peer, const char *rname);
	int move_base_cond(struct cond_entry *conds, bool peer);

	virtual bool has_peer_conds(void) { return peer_label ? true : false; }
	virtual ostream &dump_local(ostream &os);
	virtual ostream &dump_peer(ostream &os);
	virtual ostream &dump(ostream &os);
	virtual int expand_variables(void);
	virtual int gen_policy_re(Profile &prof) = 0;

	virtual bool is_mergeable(void) { return true; }
	virtual int cmp(rule_t const &rhs) const
	{
		int res = perms_rule_t::cmp(rhs);
		if (res)
			return res;
		af_rule const &trhs = (rule_cast<af_rule const &>(rhs));
		res = af - trhs.af;
		if (res)
			return res;
		res = sock_type_n - trhs.sock_type_n;
		if (res)
			return res;
		res = proto_n - trhs.proto_n;
		if (res)
			return res;
		res = null_strcmp(sock_type, trhs.sock_type);
		if (res)
			return res;
		res = null_strcmp(proto, trhs.proto);
		if (res)
			return res;
		res = null_strcmp(label, trhs.label);
		if (res)
			return res;
		return null_strcmp(peer_label, trhs.peer_label);
	};

};

#endif /* __AA_AF_RULE_H */
