/*
 *	Copyright (C) 2002-2005 Novell/SUSE
 *
 *	This program is free software; you can redistribute it and/or
 *	modify it under the terms of the GNU General Public License as
 *	published by the Free Software Foundation, version 2 of the
 *	License.
 */

#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <string.h>
#include <stdlib.h>

struct mnt_keyword_table {
	const char *keyword;
	unsigned long set;
	unsigned long clear;
};

static struct mnt_keyword_table mnt_opts_table[] = {
	{ "rw", 0, MS_RDONLY }, /* read-write */
	{ "ro", MS_RDONLY, 0 }, /* read-only */

	{ "exec",   0, MS_NOEXEC }, /* permit execution of binaries */
	{ "noexec", MS_NOEXEC, 0 }, /* don't execute binaries */

	{ "suid",   0, MS_NOSUID }, /* honor suid executables */
	{ "nosuid", MS_NOSUID, 0 }, /* don't honor suid executables */

	{ "dev",   0, MS_NODEV }, /* interpret device files  */
	{ "nodev", MS_NODEV, 0 }, /* don't interpret devices */

	{ "async", 0, MS_SYNCHRONOUS }, /* asynchronous I/O */
	{ "sync",  MS_SYNCHRONOUS, 0 }, /* synchronous I/O */

	{ "loud",   0, MS_SILENT }, /* print out messages. */
	{ "silent", MS_SILENT, 0 }, /* be quiet  */

	{ "nomand", 0, MS_MANDLOCK }, /* forbid mandatory locks on this FS */
	{ "mand",   MS_MANDLOCK, 0 }, /* allow mandatory locks on this FS */

	{ "atime",   0, MS_NOATIME }, /* update access time */
	{ "noatime", MS_NOATIME, 0 }, /* do not update access time */

	{ "noiversion", 0, MS_I_VERSION }, /* don't update inode I_version time */
	{ "iversion",   MS_I_VERSION, 0 }, /* update inode I_version time */

	{ "diratime",   0, MS_NODIRATIME }, /* update dir access times */
	{ "nodiratime", MS_NODIRATIME, 0 }, /* do not update dir access times */

	{ "nostrictatime", 0, MS_STRICTATIME }, /* kernel default atime */
	{ "strictatime",   MS_STRICTATIME, 0 }, /* strict atime semantics */

/* MS_LAZYTIME added in 4.0 kernel */
#ifdef MS_LAZYTIME
	{ "nolazytime", 0, MS_LAZYTIME },
	{ "lazytime",   MS_LAZYTIME, 0 }, /* update {a,m,c}time on the in-memory inode only */
#endif

	{ "acl",   MS_POSIXACL, 0 },
	{ "noacl", 0, MS_POSIXACL },

	{ "norelatime", 0, MS_RELATIME },
	{ "relatime",   MS_RELATIME, 0 },

	{ "dirsync", MS_DIRSYNC, 0 }, /* synchronous directory modifications */
	{ "nodirsync", 0, MS_DIRSYNC },

/* MS_NOSYMFOLLOW added in 5.10 kernel */
#ifdef MS_NOSYMFOLLOW
	{ "nosymfollow", MS_NOSYMFOLLOW, 0 },
	{ "symfollow",   0, MS_NOSYMFOLLOW },
#endif

	{ "bind",        MS_BIND,                0 }, /* remount part of the tree elsewhere */
	{ "rbind",       MS_BIND | MS_REC,       0 }, /* idem, plus mounted subtrees */
	{ "unbindable",  MS_UNBINDABLE,          0 }, /* unbindable */
	{ "runbindable", MS_UNBINDABLE | MS_REC, 0 },
	{ "private",     MS_PRIVATE,             0 }, /* private */
	{ "rprivate",    MS_PRIVATE | MS_REC,    0 },
	{ "slave",       MS_SLAVE,               0 }, /* slave */
	{ "rslave",      MS_SLAVE | MS_REC,      0 },
	{ "shared",      MS_SHARED,              0 }, /* shared */
	{ "rshared",     MS_SHARED | MS_REC,     0 },

	{ "move", MS_MOVE, 0 },

	{ "remount", MS_REMOUNT, 0 },
};

const unsigned int mnt_opts_table_size =
	sizeof(mnt_opts_table) / sizeof(struct mnt_keyword_table);


unsigned long get_mnt_opt_bit(char *key)
{
	for (unsigned int i = 0; i < mnt_opts_table_size; i++) {
		if (strcmp(mnt_opts_table[i].keyword, key) == 0) {
			return mnt_opts_table[i].set;
		}
	}
	fprintf(stderr, "FAIL: invalid option\n");
	exit(1);
}

static void usage(char *prog_name)
{
	fprintf(stderr, "Usage: %s mount|umount <source> <target> [options]\n", prog_name);
	fprintf(stderr, "Options are:\n");
	fprintf(stderr, "-o        flags sent to the mount syscall\n");
	fprintf(stderr, "-d        data sent to the mount syscall\n");
	exit(1);
}

int main(int argc, char *argv[])
{
	char *options = NULL;
	char *data = NULL;
	int index;
	int c;
	char *op, *source, *target, *token;
	unsigned long flags = 0;

	while ((c = getopt (argc, argv, "o:d:h")) != -1) {
		switch (c)
		{
		case 'o':
			options = optarg;
			break;
		case 'd':
			data = optarg;
			break;
		case 'h':
			usage(argv[0]);
			break;
		default:
			break;
		}
	}

	index = optind;
	if (argc - optind < 3) {
		fprintf(stderr, "FAIL: missing positional arguments\n");
		usage(argv[0]);
	}

	op = argv[index++];
	source = argv[index++];
	target = argv[index++];

	if (options) {
		token = strtok(options, ",");
		while (token) {
			flags |= get_mnt_opt_bit(token);
			token = strtok(NULL, ",");
		}
	}

	if (strcmp(op, "mount") == 0) {
		if (mount(source, target, "ext2", flags, data) == -1) {
			fprintf(stderr, "FAIL: mount %s on %s failed - %s\n",
				source, target,	strerror(errno));
			return errno;
		}
	} else if (strcmp(op, "umount") == 0) {
		if (umount(target) == -1) {
			fprintf(stderr, "FAIL: umount %s failed - %s\n",
				target, strerror(errno));
			return errno;
		}
	} else {
		fprintf(stderr, "usage: %s [mount|umount] loopdev mountpoint\n",
			argv[0]);
		return 1;
	}

	printf("PASS\n");

	return 0;
}
