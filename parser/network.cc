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

#include <iomanip>
#include <string>
#include <sstream>
#include <map>

#include "lib.h"
#include "parser.h"
#include "profile.h"
#include "network.h"

#define ALL_TYPES 0x43e

int parse_net_perms(const char *str_mode, perms_t *mode, int fail)
{
	return parse_X_perms("net", AA_VALID_NET_PERMS, str_mode, mode, fail);
}

/* Bleah C++ doesn't have non-trivial designated initializers so we just
 * have to make sure these are in order.  This means we are more brittle
 * but there isn't much we can do.
 */
struct sock_type_map {
	const char *name;
	int	value;
};

struct sock_type_map sock_types[] = {
	{ "none",	0 },
	{ "stream",	SOCK_STREAM },
	{ "dgram",	SOCK_DGRAM },
	{ "raw",	SOCK_RAW },
	{ "rdm",	SOCK_RDM },
	{ "seqpacket",	SOCK_SEQPACKET },
	{ "dccp",	SOCK_DCCP },
	{ "invalid",	-1 },
	{ "invalid",	-1 },
	{ "invalid",	-1 },
	{ "packet",	SOCK_PACKET },
	{ NULL, -1 },
	/*
	 * See comment above
	*/
};

int net_find_type_val(const char *type)
{
	int i;
	for (i = 0; sock_types[i].name; i++) {
		if (strcmp(sock_types[i].name, type) == 0)
			return sock_types[i].value;
	}

	return -1;
}

const char *net_find_type_name(int type)
{
	int i;
	for (i = 0; sock_types[i].name; i++) {
		if (sock_types[i].value  == type)
			return sock_types[i].name;
	}

	return NULL;
}


/* FIXME: currently just treating as a bit mask this will have to change
 * set up a table of mappings, there can be several mappings for a
 * given match.
 * currently the mapping does not set the protocol for stream/dgram to
 * anything other than 0.
 *   network inet tcp -> network inet stream 0 instead of
 *   network inet raw tcp.
 * some entries are just provided for completeness at this time
 */
/* values stolen from /etc/protocols - needs to change */
#define RAW_TCP 6
#define RAW_UDP 17
#define RAW_ICMP 1
#define RAW_ICMPv6 58

/* used by af_name.h to auto generate table entries for "name", AF_NAME
 * pair */
#define AA_GEN_NET_ENT(name, AF) \
	{name, AF, "stream",    SOCK_STREAM,    "", 0xffffff}, \
	{name, AF, "dgram",     SOCK_DGRAM,     "", 0xffffff}, \
	{name, AF, "seqpacket", SOCK_SEQPACKET, "", 0xffffff}, \
	{name, AF, "rdm",       SOCK_RDM,       "", 0xffffff}, \
	{name, AF, "raw",       SOCK_RAW,       "", 0xffffff}, \
	{name, AF, "packet",    SOCK_PACKET,    "", 0xffffff},
/*FIXME: missing {name, AF, "dccp", SOCK_DCCP, "", 0xfffffff}, */

static struct network_tuple network_mappings[] = {
	/* basic types */
	#include "af_names.h"
/* FIXME: af_names.h is missing AF_LLC, AF_TIPC */
	/* mapped types */
	{"inet",	AF_INET,	"raw",		SOCK_RAW,
	 "tcp",		1 << RAW_TCP},
	{"inet",	AF_INET,	"raw",		SOCK_RAW,
	 "udp",		1 << RAW_UDP},
	{"inet",	AF_INET,	"raw",		SOCK_RAW,
	 "icmp",	1 << RAW_ICMP},
	{"inet",	AF_INET,	"tcp",		SOCK_STREAM,
	 "",		0xffffffff},	/* should we give raw tcp too? */
	{"inet",	AF_INET,	"udp",		SOCK_DGRAM,
	 "",		0xffffffff},	/* should these be open masks? */
	{"inet",	AF_INET,	"icmp",		SOCK_RAW,
	 "",		1 << RAW_ICMP},
	{"inet6",	AF_INET6,	"tcp",		SOCK_STREAM,
	 "",		0xffffffff},
	{"inet6",	AF_INET6,	"udp",		SOCK_DGRAM,
	 "",		0xffffffff},
/* what do we do with icmp on inet6?
	{"inet6",	AF_INET,	"icmp",		SOCK_RAW,	0},
	{"inet6",	AF_INET,	"icmpv6",	SOCK_RAW,	0},
*/
	/* terminate */
	{NULL, 0, NULL, 0, NULL, 0}
};

/* The apparmor kernel patches up until 2.6.38 didn't handle networking
 * tables with sizes > AF_MAX correctly.  This could happen when the
 * parser was built against newer kernel headers and then used to load
 * policy on an older kernel.  This could happen during upgrades or
 * in multi-kernel boot systems.
 *
 * Try to detect the running kernel version and use that to determine
 * AF_MAX
 */
#define PROC_VERSION "/proc/sys/kernel/osrelease"
static size_t kernel_af_max(void) {
	char buffer[32];
	int major;
	autoclose int fd = -1;
	int res;

	if (!net_af_max_override) {
		return 0;
	}
	/* the override parameter is specifying the max value */
	if (net_af_max_override > 0)
		return net_af_max_override;

	fd = open(PROC_VERSION, O_RDONLY);
	if (fd == -1)
		/* fall back to default provided during build */
		return 0;
	res = read(fd, &buffer, sizeof(buffer) - 1);
	if (res <= 0)
		return 0;
	buffer[res] = '\0';
	res = sscanf(buffer, "2.6.%d", &major);
	if (res != 1)
		return 0;

	switch(major) {
	case 24:
	case 25:
	case 26:
		return 34;
	case 27:
		return 35;
	case 28:
	case 29:
	case 30:
		return 36;
	case 31:
	case 32:
	case 33:
	case 34:
	case 35:
		return 37;
	case 36:
	case 37:
		return 38;
	/* kernels .38 and later should handle this correctly so no
	 * static mapping needed
	 */
	default:
		return 0;
	}
}

/* Yuck. We grab AF_* values to define above from linux/socket.h because
 * they are more accurate than sys/socket.h for what the kernel actually
 * supports. However, we can't just include linux/socket.h directly,
 * because the AF_* definitions are protected with an ifdef KERNEL
 * wrapper, but we don't want to define that because that can cause
 * other redefinitions from glibc. However, because the kernel may have
 * more definitions than glibc, we need make sure AF_MAX reflects this,
 * hence the wrapping function.
 */
size_t get_af_max() {
	size_t af_max;
	/* HACK: declare that version without "create" had a static AF_MAX */
	if (!perms_create && !net_af_max_override)
		net_af_max_override = -1;

#if AA_AF_MAX > AF_MAX
	af_max = AA_AF_MAX;
#else
	af_max = AF_MAX;
#endif

	/* HACK: some kernels didn't handle network tables from parsers
	 * compiled against newer kernel headers as they are larger than
	 * the running kernel expected.  If net_override is defined check
	 * to see if there is a static max specified for that kernel
	 */
	if (net_af_max_override) {
		size_t max = kernel_af_max();
		if (max && max < af_max)
			return max;
	}

	return af_max;
}

const char *net_find_af_name(unsigned int af)
{
	size_t i;

	if (af < 0 || af > get_af_max())
		return NULL;

	for (i = 0; i < sizeof(network_mappings) / sizeof(*network_mappings); i++) {
		if (network_mappings[i].family == af)
			return network_mappings[i].family_name;
	}

	return NULL;
}

const struct network_tuple *net_find_mapping(const struct network_tuple *map,
					     const char *family,
					     const char *type,
					     const char *protocol)
{
	if (!map)
		map = network_mappings;
	else
		/* assumes it points to last entry returned */
		map++;

	for (; map->family_name; map++) {
		if (family) {
			PDEBUG("Checking family %s\n", map->family_name);
			if (strcmp(family, map->family_name) != 0)
				continue;
			PDEBUG("Found family %s\n", family);
		}
		if (type) {
			PDEBUG("Checking type %s\n", map->type_name);
			if (strcmp(type, map->type_name) != 0)
				continue;
			PDEBUG("Found type %s\n", type);
		}
		if (protocol) {
			/* allows the proto to be the "type", ie. tcp implies
			 * stream */
			if (!type) {
				PDEBUG("Checking protocol type %s\n", map->type_name);
				if (strcmp(protocol, map->type_name) == 0)
					goto match;
			}
			PDEBUG("Checking type %s protocol %s\n", map->type_name, map->protocol_name);
			if (strcmp(protocol, map->protocol_name) != 0)
				continue;
			/* fixme should we allow specifying protocol by #
			 * without needing the protocol mapping? */
		}

		/* if we get this far we have a match */
	match:
		return map;
	}

	return NULL;
}

void network_rule::set_netperm(unsigned int family, unsigned int type)
{
	if (type > SOCK_PACKET) {
		/* setting mask instead of a bit */
		network_perms[family] |= type;
	} else
		network_perms[family] |= 1 << type;
}

network_rule::network_rule(const char *family, const char *type,
			   const char *protocol):
	dedup_perms_rule_t(AA_CLASS_NETV8)
{
	if (!family && !type && !protocol) {
		size_t family_index;
		for (family_index = AF_UNSPEC; family_index < get_af_max(); family_index++) {
			network_map[family_index].push_back({ family_index, 0xFFFFFFFF, 0xFFFFFFFF });
			set_netperm(family_index, 0xFFFFFFFF);
		}
	} else {
		const struct network_tuple *mapping = NULL;
		while ((mapping = net_find_mapping(mapping, family, type, protocol))) {
			network_map[mapping->family].push_back({ mapping->family, mapping->type, mapping->protocol });
			set_netperm(mapping->family, mapping->type);
		}

		if (type == NULL && network_map.empty()) {
			while ((mapping = net_find_mapping(mapping, type, family, protocol))) {
				network_map[mapping->family].push_back({ mapping->family, mapping->type, mapping->protocol });
				set_netperm(mapping->family, mapping->type);
			}
		}

		if (network_map.empty())
			yyerror(_("Invalid network entry."));
	}
}

network_rule::network_rule(unsigned int family, unsigned int type):
	dedup_perms_rule_t(AA_CLASS_NETV8)
{
	network_map[family].push_back({ family, type, 0xFFFFFFFF });
	set_netperm(family, type);
}

ostream &network_rule::dump(ostream &os)
{
	class_rule_t::dump(os);

	unsigned int count = sizeof(sock_types)/sizeof(sock_types[0]);
	unsigned int mask = ~((1 << count) -1);
	unsigned int j;

	/* This can only be set by an unqualified network rule */
	if (network_map.find(AF_UNSPEC) != network_map.end()) {
		os << ",\n";
		return os;
	}

	for (const auto& perm : network_perms) {
		unsigned int family = perm.first;
		unsigned int type = perm.second;

		const char *family_name = net_find_af_name(family);
		if (family_name)
			os << " " << family_name;
		else
			os << " #" << family;

		/* All types/protocols */
		if (type == 0xffffffff || type == ALL_TYPES)
			continue;

		printf(" {");

		for (j = 0; j < count; j++) {
			const char *type_name;
			if (type & (1 << j)) {
				type_name = sock_types[j].name;
				if (type_name)
					os << " " << type_name;
				else
					os << " #" << j;
			}
		}
		if (type & mask)
			os << " #" << std::hex << (type & mask);

		printf(" }");
	}

	os << ",\n";

	return os;
}


int network_rule::expand_variables(void)
{
	return 0;
}

void network_rule::warn_once(const char *name)
{
	rule_t::warn_once(name, "network rules not enforced");
}

bool network_rule::gen_net_rule(Profile &prof, u16 family, unsigned int type_mask) {
	std::ostringstream buffer;
	std::string buf;

	buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << AA_CLASS_NETV8;
	buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << ((family & 0xff00) >> 8);
	buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << (family & 0xff);
	if (type_mask > 0xffff) {
		buffer << "..";
	} else {
		buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << ((type_mask & 0xff00) >> 8);
		buffer << "\\x" << std::setfill('0') << std::setw(2) << std::hex << (type_mask & 0xff);
	}
	buf = buffer.str();

	if (!prof.policy.rules->add_rule(buf.c_str(), rule_mode == RULE_DENY, map_perms(AA_VALID_NET_PERMS),
					 dedup_perms_rule_t::audit == AUDIT_FORCE ? map_perms(AA_VALID_NET_PERMS) : 0,
					 parseopts))
		return false;

	return true;
}

int network_rule::gen_policy_re(Profile &prof)
{
	std::ostringstream buffer;
	std::string buf;

	if (!features_supports_networkv8) {
		warn_once(prof.name);
		return RULE_NOT_SUPPORTED;
	}

	for (const auto& perm : network_perms) {
		unsigned int family = perm.first;
		unsigned int type = perm.second;

		if (type > 0xffff) {
			if (!gen_net_rule(prof, family, type))
				goto fail;
		} else {
			int t;
			/* generate rules for types that are set */
			for (t = 0; t < 16; t++) {
				if (type & (1 << t)) {
					if (!gen_net_rule(prof, family, t))
						goto fail;
				}
			}
		}

	}
	return RULE_OK;

fail:
	return RULE_ERROR;

}

/* initialize static members */
unsigned int *network_rule::allow = NULL;
unsigned int *network_rule::audit = NULL;
unsigned int *network_rule::deny = NULL;
unsigned int *network_rule::quiet = NULL;

bool network_rule::alloc_net_table()
{
	if (allow)
		return true;
	allow = (unsigned int *) calloc(get_af_max(), sizeof(unsigned int));
	audit = (unsigned int *) calloc(get_af_max(), sizeof(unsigned int));
	deny = (unsigned int *) calloc(get_af_max(), sizeof(unsigned int));
	quiet = (unsigned int *) calloc(get_af_max(), sizeof(unsigned int));
	if (!allow || !audit || !deny || !quiet)
		return false;

	return true;
}

/* update is required because at the point of the creation of the
 * network_rule object, we don't have owner, rule_mode, or audit
 * set.
 */
void network_rule::update_compat_net(void)
{
	if (!alloc_net_table())
		yyerror(_("Memory allocation error."));

	for (auto& nm: network_map) {
		for (auto& entry : nm.second) {
			if (entry.type > SOCK_PACKET) {
				/* setting mask instead of a bit */
				if (rule_mode == RULE_DENY) {
					deny[entry.family] |= entry.type;
					if (dedup_perms_rule_t::audit != AUDIT_FORCE)
						quiet[entry.family] |= entry.type;
				} else {
					allow[entry.family] |= entry.type;
					if (dedup_perms_rule_t::audit == AUDIT_FORCE)
						audit[entry.family] |= entry.type;
				}
			} else {
				if (rule_mode == RULE_DENY) {
					deny[entry.family] |= 1 << entry.type;
					if (dedup_perms_rule_t::audit != AUDIT_FORCE)
						quiet[entry.family] |= 1 << entry.type;
				} else {
					allow[entry.family] |= 1 << entry.type;
					if (dedup_perms_rule_t::audit == AUDIT_FORCE)
						audit[entry.family] |= 1 << entry.type;
				}
			}
		}
	}
}

static int cmp_network_map(std::unordered_map<unsigned int, perms_t> lhs,
			   std::unordered_map<unsigned int, perms_t> rhs)
{
	int res;
	size_t family_index;
	for (family_index = AF_UNSPEC; family_index < get_af_max(); family_index++) {
		res = lhs[family_index] - rhs[family_index];
		if (res)
			return res;
	}
	return 0;
}

int network_rule::cmp(rule_t const &rhs) const
{
	int res = dedup_perms_rule_t::cmp(rhs);
	if (res)
		return res;
	network_rule const &nrhs = rule_cast<network_rule const &>(rhs);
	return cmp_network_map(network_perms, nrhs.network_perms);
};
