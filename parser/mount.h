/*
 *   Copyright (c) 2010
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

#ifndef __AA_MOUNT_H
#define __AA_MOUNT_H

#include <ostream>
#include <vector>
#include <algorithm>

#include "parser.h"
#include "rule.h"


#define MS_RDONLY	(1 << 0)
#define MS_RW		0
#define MS_NOSUID	(1 << 1)
#define MS_SUID		0
#define MS_NODEV	(1 << 2)
#define MS_DEV		0
#define MS_NOEXEC	(1 << 3)
#define MS_EXEC		0
#define MS_SYNCHRONOUS		(1 << 4)
#define MS_ASYNC	0
#define MS_REMOUNT	(1 << 5)
#define MS_MAND		(1 << 6)
#define MS_NOMAND	0
#define MS_DIRSYNC	(1 << 7)
#define MS_SYMFOLLOW	0
#define MS_NOSYMFOLLOW	(1 << 8)
#define MS_NODIRSYNC	0
#define MS_NOATIME	(1 << 10)
#define MS_ATIME	0
#define MS_NODIRATIME	(1 << 11)
#define MS_DIRATIME	0
#define MS_BIND		(1 << 12)
#define MS_MOVE		(1 << 13)
#define MS_REC		(1 << 14)
#define MS_VERBOSE	(1 << 15)
#define MS_SILENT	(1 << 15)
#define MS_LOAD		0
#define MS_ACL		(1 << 16)
#define MS_NOACL	0
#define MS_UNBINDABLE	(1 << 17)
#define MS_PRIVATE	(1 << 18)
#define MS_SLAVE	(1 << 19)
#define MS_SHARED	(1 << 20)
#define MS_RELATIME	(1 << 21)
#define MS_NORELATIME	0
#define MS_IVERSION	(1 << 23)
#define MS_NOIVERSION	0
#define MS_STRICTATIME	(1 << 24)
#define MS_LAZYTIME	(1 << 25)
#define MS_NOUSER	(1 << 31)
#define MS_USER		0

/* Only use MS_REC when defining these macros. Please use the macros from here
 * on and don't make assumptions about the presence of MS_REC. */
#define MS_RBIND	(MS_BIND | MS_REC)
#define MS_RUNBINDABLE	(MS_UNBINDABLE | MS_REC)
#define MS_RPRIVATE	(MS_PRIVATE | MS_REC)
#define MS_RSLAVE	(MS_SLAVE | MS_REC)
#define MS_RSHARED	(MS_SHARED | MS_REC)

#define MS_ALL_FLAGS	(MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC | \
			 MS_SYNCHRONOUS | MS_REMOUNT | MS_MAND | MS_DIRSYNC | \
			 MS_NOSYMFOLLOW | \
			 MS_NOATIME | MS_NODIRATIME | MS_BIND | MS_RBIND | \
			 MS_MOVE | MS_VERBOSE | MS_ACL | \
			 MS_UNBINDABLE | MS_RUNBINDABLE | \
			 MS_PRIVATE | MS_RPRIVATE | \
			 MS_SLAVE | MS_RSLAVE | MS_SHARED | MS_RSHARED | \
			 MS_RELATIME | MS_IVERSION | MS_STRICTATIME | \
			 MS_LAZYTIME | MS_USER)

/* set of flags we don't use but define (but not with the kernel values)
 *  for MNT_FLAGS
 */
#define MS_ACTIVE	0
#define MS_BORN		0
#define MS_KERNMOUNT	0

/* from kernel fs/namespace.c - set of flags masked off */
#define MNT_FLAGS	(MS_NOSUID | MS_NOEXEC | MS_NODEV | MS_ACTIVE | \
			 MS_BORN | MS_NOATIME | MS_NODIRATIME | MS_RELATIME| \
			 MS_KERNMOUNT | MS_STRICTATIME)

#define MS_BIND_FLAGS (MS_BIND | MS_RBIND)
#define MS_MAKE_CMDS (MS_UNBINDABLE | MS_RUNBINDABLE | \
			MS_PRIVATE | MS_RPRIVATE | \
			MS_SLAVE | MS_RSLAVE | MS_SHARED | MS_RSHARED)
#define MS_MAKE_FLAGS  (MS_ALL_FLAGS & ~(MNT_FLAGS))
#define MS_MOVE_FLAGS (MS_MOVE)

#define MS_CMDS (MS_MOVE | MS_REMOUNT | MS_BIND | MS_RBIND | MS_MAKE_CMDS)
/*
 * This allows MS_MAKE_CMDS, by design: while remount and make-* shouldn't be
 * used together, real-world applications do use them together, and the Linux
 * kernel ignores the make-* flags when doing a remount instead of returning
 * EINVAL. See https://bugs.launchpad.net/apparmor/+bug/2091424 for an example.
 */
#define MS_REMOUNT_FLAGS (MS_ALL_FLAGS & ~MS_MOVE_FLAGS)
#define MS_NEW_FLAGS (MS_ALL_FLAGS & ~MS_CMDS)

#define MNT_SRC_OPT 1
#define MNT_DST_OPT 2

#define MNT_COND_FSTYPE 1
#define MNT_COND_OPTIONS 2

#define AA_MAY_PIVOTROOT 1
#define AA_MAY_MOUNT 2
#define AA_MAY_UMOUNT 4
#define AA_MATCH_CONT 0x40
#define AA_AUDIT_MNT_DATA AA_MATCH_CONT
#define AA_DUMMY_REMOUNT 0x40000000	/* dummy perm for remount rule - is
					 * remapped to a mount option*/


class mnt_rule: public perms_rule_t {
	int gen_policy_remount(Profile &prof, int &count, unsigned int flags,
			       unsigned int opt_flags);
	int gen_policy_bind_mount(Profile &prof, int &count, unsigned int flags,
				  unsigned int opt_flags);
	int gen_policy_change_mount_type(Profile &prof, int &count,
					 unsigned int flags,
					 unsigned int opt_flags);
	int gen_policy_move_mount(Profile &prof, int &count, unsigned int flags,
				  unsigned int opt_flags);
	int gen_policy_new_mount(Profile &prof, int &count, unsigned int flags,
				 unsigned int opt_flags);
	int gen_flag_rules(Profile &prof, int &count, unsigned int flags,
			   unsigned int opt_flags);
public:
	char *mnt_point;
	char *device;
	char *trans;
	struct value_list *dev_type;
	struct value_list *opts;

	std::vector<unsigned int> flagsv, opt_flagsv;


	mnt_rule(struct cond_entry *src_conds, char *device_p,
		   struct cond_entry *dst_conds unused, char *mnt_point_p,
		   perm32_t perms_p);
	~mnt_rule() override
	{
		free_value_list(opts);
		free_value_list(dev_type);
		free(device);
		free(mnt_point);
		free(trans);
	}

	bool valid_prefix(const prefixes &p, const char *&error) override {
		if (p.owner != OWNER_UNSPECIFIED) {
			error = "owner prefix not allowed on mount rules";
			return false;
		}
		return true;
	};
	ostream &dump(ostream &os) override;
	int expand_variables(void) override;
	int gen_policy_re(Profile &prof) override;
	void post_parse_profile(Profile &prof unused) override;

	bool is_mergeable(void) override { return true; }
	int cmp(rule_t const &rhs) const override;

	// for now use default merge/dedup

protected:
	void warn_once(const char *name) override;
};

int is_valid_mnt_cond(const char *name, int src);


#endif /* __AA_MOUNT_H */
