#include <stdio.h>
#include <string.h>
#include <unistd.h>

void print_usage() {
    fprintf(stderr, "Usage: ./complain (read|exec) [args]\n");
}

int main(int argc, char **argv) {
    if (argc < 3) {
        print_usage();
        return 1;
    }
    if (strcmp(argv[1], "read") == 0) {
        FILE *file = fopen(argv[2], "r");
        if (file == NULL) {
            perror("FAIL: Could not open file");
            return 2;
        }
        long file_len = ftell(file);
        if (file_len == -1) {
            perror("FAIL: Could not get file len");
            fclose(file);
            return 1;
        }
        // Don't need to do anything else for now
        fprintf(stderr, "PASS\n");
        return 0;
    } else if (strcmp(argv[1], "exec") == 0) {
        execvp(argv[2], &argv[2]);
        // execvp failed
        fprintf(stderr, "FAIL: execvp of %s failed\n", argv[1]);
        return 1;
    } else {
        print_usage();
        return 1;
    }
}