#include <aalogparse.h>
#include <string.h>

#include "private.h"

const char* log_line = "[23342.075380] audit: type=1400 audit(1725487203.971:1831): apparmor=\"DENIED\" operation=\"open\" class=\"file\" profile=\"snap-update-ns.firmware-updater\" name=\"/proc/202964/maps\" pid=202964 comm=\"5\" requested_mask=\"r\" denied_mask=\"r\" fsuid=1000 ouid=0";

int main(void) {
    int rc = 0;

    /* Very basic test to ensure we can do aalogparse stuff in C++ */
    aa_log_record *record = parse_record(log_line);
    MY_TEST(record != NULL, "Log failed to parse");
    MY_TEST(record->version == AA_RECORD_SYNTAX_V2, "Log should have parsed as v2 form");
    MY_TEST(record->aa_namespace == NULL, "Log should have NULL namespace");
    MY_TEST((record->rule_class != NULL) && (strcmp(record->rule_class, "file") == 0), "Log should have file class");
    free_record(record);

    return rc;
}