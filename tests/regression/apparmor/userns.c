/*
 * Copyright (C) 2022 Canonical, Ltd.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of version 2 of the GNU General Public
 * License published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, contact Canonical Ltd.
 */

#define _GNU_SOURCE
#include <sched.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <linux/limits.h>
#include "pipe_helper.h"

static void usage(char *pname)
{
	fprintf(stderr, "Usage: %s [options]\n", pname);
	fprintf(stderr, "Options can be:\n");
	fprintf(stderr, "    -c   create user namespace using clone\n");
	fprintf(stderr, "    -u   create user namespace using unshare\n");
	fprintf(stderr, "    -s   create user namespace using setns. requires the path of binary that will create the user namespace\n");
	fprintf(stderr, "    -p   named pipe path. used by setns\n");
	exit(EXIT_FAILURE);
}

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

static int child(void *arg)
{
	return EXIT_SUCCESS;
}

#ifndef __NR_pidfd_open
#define __NR_pidfd_open 434   /* System call # on most architectures */
#endif

static int
pidfd_open(pid_t pid, unsigned int flags)
{
	return syscall(__NR_pidfd_open, pid, flags);
}

int userns_setns(char *client, char *pipename)
{
	int userns, exit_status, ret;
	char *parentpipe = NULL, *childpipe = NULL;
	int parentpipefd;

	if (get_pipes(pipename, &parentpipe, &childpipe) == -1) {
		fprintf(stderr, "FAIL - failed to allocate pipes\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (mkfifo(parentpipe, 0666) == -1)
		perror("FAIL - setns parent mkfifo");

	/* exec the client */
	int pid = fork();
	if (pid == -1) {
		perror("FAIL - could not fork");
		ret = EXIT_FAILURE;
		goto out;
	} else if (!pid) {
		execl(client, client, pipename, NULL);
		printf("FAIL %d - execlp %s %s- %m\n", getuid(), client, pipename);
		ret = EXIT_FAILURE;
		goto out;
	}

	parentpipefd = open_read_pipe(parentpipe);
	if (parentpipefd == -1) {
		fprintf(stderr, "FAIL - couldn't open parent pipe\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (read_from_pipe(parentpipefd) == -1) { // wait for child to unshare
		fprintf(stderr, "FAIL - parent could not read from pipe\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	userns = pidfd_open(pid, 0);
	if (userns == -1) {
		perror("FAIL - pidfd_open");
		ret = EXIT_FAILURE;
		goto out;
	}

	// enter child namespace
	if (setns(userns, CLONE_NEWUSER) == -1) {
		perror("FAIL - setns");
		ret = EXIT_FAILURE;
	}

	if (write_to_pipe(childpipe) == -1) { // let child finish
		fprintf(stderr, "FAIL - child could not write in pipe\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (waitpid(pid, &exit_status, 0) == -1) {
		perror("FAIL - setns waitpid");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (WIFEXITED(exit_status)) {
		if (WEXITSTATUS(exit_status) != 0) {
			fprintf(stderr, "FAIL - setns child ended with failure %d\n", exit_status);
			ret = EXIT_FAILURE;
			goto out;
		}
	}

	ret = EXIT_SUCCESS;
out:
	if (unlink(parentpipe) == -1)
		perror("FAIL - could not remove parentpipe");
	free(parentpipe);
	free(childpipe);
	return ret;
}

int userns_unshare()
{
	if (unshare(CLONE_NEWUSER) == -1) {
		perror("FAIL - unshare");
		return EXIT_FAILURE;
	}
	return child(NULL);
}

int userns_clone()
{
	pid_t child_pid;
	int child_exit;

	child_pid = clone(child, child_stack + STACK_SIZE,
			  CLONE_NEWUSER | SIGCHLD, NULL);
	if (child_pid == -1) {
		perror("FAIL - clone");
		return EXIT_FAILURE;
	}

	if (waitpid(child_pid, &child_exit, 0) == -1) {
		perror("FAIL - clone waitpid");
		return EXIT_FAILURE;
	}

	if (WIFEXITED(child_exit)) {
		if (WEXITSTATUS(child_exit) != EXIT_SUCCESS) {
			fprintf(stderr, "FAIL - child ended with failure %d\n", child_exit);
			return EXIT_FAILURE;
		}
	}

	return EXIT_SUCCESS;
}

enum op {
	CLONE,
	UNSHARE,
	SETNS,
};

int main(int argc, char *argv[])
{
	int opt, ret = 0, op;
	char *client = "userns_setns";
	char *pipename = "/tmp/userns_pipe";

	while ((opt = getopt(argc, argv, "us:cp:")) != -1) {
		switch (opt) {
		case 'c': op = CLONE;	break;
		case 'u': op = UNSHARE;	break;
		case 's':
			op = SETNS;
			client = optarg;
			break;
		case 'p':
			pipename = optarg;
			break;
		default:  usage(argv[0]);
		}
	}

	if (op == CLONE)
		ret = userns_clone();
	else if (op == UNSHARE)
		ret = userns_unshare();
	else if (op == SETNS) {
		ret = userns_setns(client, pipename);
	}
	else
		fprintf(stderr, "FAIL - user namespace method not defined\n");

	if (ret == EXIT_SUCCESS)
		printf("PASS\n");
	return ret;
}
