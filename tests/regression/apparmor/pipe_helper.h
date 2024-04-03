#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>

int get_pipes(const char *pipename, char **parentpipe, char **childpipe)
{
	if (asprintf(parentpipe, "%s1", pipename) == -1)
		return -1;
	if (asprintf(childpipe, "%s2", pipename) == -1)
		return -1;
	return 0;
}

int open_read_pipe(char *pipename)
{
	int fd;
	fd = open(pipename, O_RDONLY | O_NONBLOCK);
	if (fd == -1) {
		perror("FAIL - open read pipe");
		return EXIT_FAILURE;
	}
	return fd;
}

int read_from_pipe(int fd)
{
	int ret;
	char buf;
	fd_set set;
	struct timeval timeout;

	if (fd == -1) {
		fprintf(stderr, "FAIL - invalid read fd\n");
		return EXIT_FAILURE;
	}

	FD_ZERO(&set);
	FD_SET(fd, &set);

	timeout.tv_sec = 3;
	timeout.tv_usec = 0;

	ret = select(fd + 1, &set, NULL, NULL, &timeout);
	if (ret == -1) {
		perror("FAIL - select");
		goto err;
	} else if (ret == 0) {
		fprintf(stderr, "FAIL - read timeout\n");
		goto err;
	} else {
		if (read(fd, &buf, 1) == -1) { // wait for client to unshare
			perror("FAIL - read pipe");
			close(fd);
			return EXIT_FAILURE;
		}
	}
	return EXIT_SUCCESS;
err:
	return EXIT_FAILURE;
}

int write_to_pipe(char *pipename)
{
	int fd;

	fd = open(pipename, O_WRONLY | O_NONBLOCK);
	if (fd == -1) {
		fprintf(stderr, "FAIL - open write pipe %s - %m\n", pipename);
		return EXIT_FAILURE;
	}
	close(fd);
	return EXIT_SUCCESS;
}
