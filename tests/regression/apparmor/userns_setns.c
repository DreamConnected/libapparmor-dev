#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include "pipe_helper.h"

int main(int argc, char *argv[])
{
	int ret;
	char *pipename = "/tmp/userns_pipe";
	char *parentpipe = NULL, *childpipe = NULL;
	int childpipefd;

	if (argc > 1)
		pipename = argv[1];

	if (get_pipes(pipename, &parentpipe, &childpipe) == -1) {
		fprintf(stderr, "FAIL - failed to allocate pipes\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (mkfifo(childpipe, 0666) == -1)
		perror("FAIL - setns child mkfifo");

	childpipefd = open_read_pipe(childpipe);
	if (childpipefd == -1) {
		fprintf(stderr, "FAIL - couldn't open child pipe\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (unshare(CLONE_NEWUSER) == -1) {
		perror("FAIL - unshare");
		ret = EXIT_FAILURE;
		goto out;
	}

	if (write_to_pipe(parentpipe) == -1) { // let parent know user namespace is created
		fprintf(stderr, "FAIL - child could not write in pipe\n");
		ret = EXIT_FAILURE;
		goto out;
	}
	if (read_from_pipe(childpipefd) == -1) { // wait for parent tell child can finish
		fprintf(stderr, "FAIL - child could not read from pipe\n");
		ret = EXIT_FAILURE;
		goto out;
	}

	ret = EXIT_SUCCESS;
out:
	if (unlink(childpipe) == -1)
		perror("FAIL - could not remove childpipe");
	free(parentpipe);
	free(childpipe);
	return ret;
}
