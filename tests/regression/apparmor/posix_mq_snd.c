#define _GNU_SOURCE
#include <mqueue.h>
#include <stdlib.h>

#include "posix_mq.h"
#include "pipe_helper.h"

int main(int argc, char * argv[])
{
	mqd_t mqd;
	char *queuename = QNAME;
	int pipefd;

	if (argc > 1) {
		queuename = argv[1];
	}
	if (argc > 2) {
		pipefd = atoi(argv[2]);
		if (read_from_pipe(pipefd) == -1) { // wait for receiver to mq_notify
			fprintf(stderr, "FAIL - could not read from pipe\n");
			return 1;
		}
	}

	mqd = mq_open(queuename, O_WRONLY);
	if (mqd == (mqd_t) -1) {
		perror("FAIL sender - could not open mq");
		return 1;
	}

	if (mq_send(mqd, msg, strnlen(msg, BUF_SIZE), 0) == -1) {
		perror("FAIL sender - could not send");
		return 1;
	}

	if (mq_close(mqd) == (mqd_t) -1) {
		perror("FAIL sender - could not close mq");
		return 1;
	}

	//printf("PASS client\n");
	return 0;
}
