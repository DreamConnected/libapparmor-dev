#include <sys/apparmor.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Simple program that checks if its own confinement has a string
int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "FAIL: usage: allow_all [expected_label] [expected mode]\n");
        return 1;
    }

    char *label;
    char *mode;
    aa_getcon(&label, &mode);

    // Now check our own confinement
    if (strcmp(label, argv[1]) == 0 && strcmp(mode, argv[2]) == 0) {
        free(label);
        puts("PASS");
        return 0;
    } else {
        fprintf(stderr, "FAIL: expected confinement %s (%s), got label %s (%s)\n",
            argv[1], argv[2], label, mode);
        free(label);
        return 1;
    }

    return 0;
}