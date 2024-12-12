#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <sys/stat.h>
#include <sys/xattr.h>

void print_usage() {
    fprintf(stderr, "Usage: ./complain (operation) [args]\n");
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
        unsigned char* discard_read_buf[8];
        fread(discard_read_buf, 8, 1, file);
        if (ferror(file)) {
            perror("FAIL: Could not perform file read");
            fclose(file);
            return 1;
        }
        fclose(file);
    } else if (strcmp(argv[1], "write") == 0) {
        FILE *file = fopen(argv[2], "w");
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
        const char* write_buf = "pahoehoe";
        fwrite(write_buf, 9, 1, file);
        if (ferror(file)) {
            perror("FAIL: Could not perform file write");
            fclose(file);
            return 1;
        }
        fclose(file);
    } else if (strcmp(argv[1], "exec") == 0) {
        execvp(argv[2], &argv[2]);
        // execvp failed
        fprintf(stderr, "FAIL: execvp of %s failed\n", argv[1]);
        return 1;
    } else if (strcmp(argv[1], "stat") == 0) {
        struct stat unused;
        if (stat(argv[2], &unused) == -1) {
            perror("FAIL: Could not perform file stat");
            return 1;
        }
    } else if (strcmp(argv[1], "xattr") == 0) {
        // Only query the size-that should be enough to exercise the syscall
        if (listxattr(argv[2], NULL, 0) < 0) {
            perror("FAIL: Could not get file xattrs");
            return 1;
        }
    } else if (strcmp(argv[1], "rename") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Error: rename operation needs two arguments\n");
            return 1;
        }
        if (rename(argv[2], argv[3]) == -1) {
            perror("FAIL: Could not perform file rename");
            return 1;
        }
    } else if (strcmp(argv[1], "unlink") == 0) {
        if (unlink(argv[1]) == -1) {
            perror("FAIL: Could not perform file removal");
            return 1;
        }
    } else {
        print_usage();
        return 1;
    }
    fprintf(stderr, "PASS\n");
    return 0;
}