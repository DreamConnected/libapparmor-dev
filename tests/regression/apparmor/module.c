/*
 * Copyright (C) 2021 Canonical, Ltd.
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

#include <stdio.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <string.h>

#define init_module(module_image, len, param_values) syscall(__NR_init_module, module_image, len, param_values)
#define finit_module(fd, param_values, flags) syscall(__NR_finit_module, fd, param_values, flags)
#define delete_module(name, flags) syscall(__NR_delete_module, name, flags)

#define REQUEST_MODULE "./module_test/request.ko"
#define MODULE_NAME_LEN 256

void rmmod(const char *name)
{
	int i;
	char modname[MODULE_NAME_LEN];

	/* get module name from file name */
	for (i = 0; i < (MODULE_NAME_LEN-1) && name[i] != '\0' && name[i] != '.'; i++)
		modname[i] = (name[i] == '-') ? '_' : name[i];
	modname[i] = '\0';

	if (delete_module(modname, O_NONBLOCK) != 0)
		fprintf(stderr, "Could not remove module %s\n", modname);
}

int load_file(const char *path, const char *param)
{
	int rc = 0;

	int fd = open(path, O_RDONLY|O_CLOEXEC);
	if (fd < 0) {
		perror("FAIL - open");
		rc = 1;
		goto out;
	}

	rc = finit_module(fd, param, 0);
	if (rc == -1) {
		perror("FAIL - finit_module");
		rc = 2;
		goto out_close;
	}

	rmmod(basename(path));

out_close:
	close(fd);

out:
	return rc;
}

int request(const char *name)
{
	int rc = 0;

	char *param;
	rc = asprintf(&param, "request=%s", name);
	if (rc < 0) {
		perror("FAIL - asprintf");
		rc = 1;
		goto out;
	}

	rc = load_file(REQUEST_MODULE, param);
	if (rc < 0) {
		perror("FAIL - load_file");
		rc = 2;
		goto out_free;
	}

	rmmod(name);

out_free:
	free(param);

out:
	return rc;
}

int load_data(const char *path)
{
	void *buf = 0;
	struct stat sb;
	int rc = 0;

	int fd = open(path, O_RDONLY|O_CLOEXEC);
	if (fd < 0) {
		perror("FAIL - open");
		rc = 1;
		goto out;
	}

	rc = fstat(fd, &sb);
	if (rc == -1) {
		perror("FAIL - fstat");
		rc = 2;
		goto out_close;
	}

	buf = mmap(0, sb.st_size, PROT_READ|PROT_EXEC, MAP_PRIVATE, fd, 0);
	if (buf == 0) {
		perror("FAIL - mmap");
		rc = 3;
		goto out_close;
	}

	rc = init_module(buf, sb.st_size, "");
	if (rc == -1) {
		perror("FAIL - init_module");
		rc = 4;
		goto out_free;
	}

	rmmod(basename(path));

out_free:
	munmap(buf, sb.st_size);

out_close:
	close(fd);

out:
	return rc;
}

void print_usage(char *prog_name)
{
	fprintf(stderr,
		"usage: %s <MODULE_LOAD_MODE> <MODULE>\n\n"
		"<MODULE_LOAD_MODE>\tMethod for loading specified module.\n"
		"\t\t\tCan be load_data, load_file or request.\n"
		"<MODULE>\t\tName or path of the module to be loaded.\n\n",
		prog_name);
}

int main(int argc, char *argv[])
{
	int rc = 0;

	if (argc < 3){
		print_usage(argv[0]);
		return 1;
	}

	if (strncmp(argv[1], "load_data", 10) == 0){
		rc = load_data(argv[2]);
	} else if (strncmp(argv[1], "load_file", 10) == 0){
		rc = load_file(argv[2], "");
	} else if (strncmp(argv[1], "request", 7) == 0){
		rc = request(argv[2]);
	} else {
		fprintf(stderr, "FAIL - Invalid module loading mode.\n\n");
		print_usage(argv[0]);
		return 1;
	}

	if (rc != 0)
		return rc;

	printf("PASS\n");
	return rc;
}
