#include <pthread.h>
#include <string.h>

#include <aalogparse.h>

#include "private.h"

const char* log_line = "[23342.075380] audit: type=1400 audit(1725487203.971:1831): apparmor=\"DENIED\" operation=\"open\" class=\"file\" profile=\"snap-update-ns.firmware-updater\" name=\"/proc/202964/maps\" pid=202964 comm=\"5\" requested_mask=\"r\" denied_mask=\"r\" fsuid=1000 ouid=0";
const char* log_line_2 = "[ 4074.372559] audit: type=1400 audit(1725553393.143:793): apparmor=\"DENIED\" operation=\"capable\" class=\"cap\" profile=\"/usr/lib/snapd/snap-confine\" pid=19034 comm=\"snap-confine\" capability=12  capname=\"net_admin\"";

static int pthread_barrier_ok(int barrier_result) {
	return barrier_result == 0 || barrier_result == PTHREAD_BARRIER_SERIAL_THREAD;
}

static int nullcmp_and_strcmp(const void *s1, const void *s2)
{
	/* Return 0 if both pointers are NULL & non-zero if only one is NULL */
	if (!s1 || !s2)
		return s1 != s2;

	return strcmp(s1, s2);
}

int aa_log_record_eq(aa_log_record *record1, aa_log_record *record2) {
	int are_eq = 1;

	are_eq &= (record1->version == record2->version);
	are_eq &= (record1->event == record2->event);
	are_eq &= (record1->pid == record2->pid);
	are_eq &= (record1->peer_pid == record2->peer_pid);
	are_eq &= (record1->task == record2->task);
	are_eq &= (record1->magic_token == record2->magic_token);
	are_eq &= (record1->epoch == record2->epoch);
	are_eq &= (record1->audit_sub_id == record2->audit_sub_id);

	are_eq &= (record1->bitmask == record2->bitmask);
	are_eq &= (nullcmp_and_strcmp(record1->audit_id, record2->audit_id) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->operation, record2->operation) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->denied_mask, record2->denied_mask) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->requested_mask, record2->requested_mask) == 0);
	are_eq &= (record1->fsuid == record2->fsuid);
	are_eq &= (record1->ouid == record2->ouid);
	are_eq &= (nullcmp_and_strcmp(record1->profile, record2->profile) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->peer_profile, record2->peer_profile) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->comm, record2->comm) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->name, record2->name) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->name2, record2->name2) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->namespace, record2->namespace) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->attribute, record2->attribute) == 0);
	are_eq &= (record1->parent == record2->parent);
	are_eq &= (nullcmp_and_strcmp(record1->info, record2->info) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->peer_info, record2->peer_info) == 0);
	are_eq &= (record1->error_code == record2->error_code);
	are_eq &= (nullcmp_and_strcmp(record1->active_hat, record2->active_hat) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->net_family, record2->net_family) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->net_protocol, record2->net_protocol) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->net_sock_type, record2->net_sock_type) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->net_local_addr, record2->net_local_addr) == 0);
	are_eq &= (record1->net_local_port == record2->net_local_port);
	are_eq &= (nullcmp_and_strcmp(record1->net_foreign_addr, record2->net_foreign_addr) == 0);
	are_eq &= (record1->net_foreign_port == record2->net_foreign_port);

	are_eq &= (nullcmp_and_strcmp(record1->execpath, record2->execpath) == 0);

	are_eq &= (nullcmp_and_strcmp(record1->dbus_bus, record2->dbus_bus) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->dbus_path, record2->dbus_path) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->dbus_interface, record2->dbus_interface) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->dbus_member, record2->dbus_member) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->signal, record2->signal) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->peer, record2->peer) == 0);

	are_eq &= (nullcmp_and_strcmp(record1->fs_type, record2->fs_type) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->flags, record2->flags) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->src_name, record2->src_name) == 0);

	are_eq &= (nullcmp_and_strcmp(record1->class, record2->class) == 0);

	are_eq &= (nullcmp_and_strcmp(record1->net_addr, record2->net_addr) == 0);
	are_eq &= (nullcmp_and_strcmp(record1->peer_addr, record2->peer_addr) == 0);
	return are_eq;
}

typedef struct {
	const char* log;
	pthread_barrier_t *barrier;
} pthread_parse_args;

void* pthread_parse_log(void* args) {
	pthread_parse_args *args_real = (pthread_parse_args *) args;
	int barrier_wait_result = pthread_barrier_wait(args_real->barrier);
	/* Return NULL and fail test if barrier wait fails */
	if (!pthread_barrier_ok(barrier_wait_result)) {
		return NULL;
	}
	aa_log_record *record = parse_record(args_real->log);
	return (void*) record;
}

#define NUM_THREADS 16

int main(void) {
	pthread_t thread_ids[NUM_THREADS];
	pthread_barrier_t barrier;
	int barrier_wait_result;
	aa_log_record* parsed_logs[NUM_THREADS];
	int rc = 0;
	/* Set up arguments to be passed to threads */
	pthread_parse_args args = {.log=log_line, .barrier=&barrier};
	pthread_parse_args args2 = {.log=log_line_2, .barrier=&barrier};

	MY_TEST(NUM_THREADS > 2, "Test requires more than 2 threads");

	/* Use barrier to synchronize the start of log parsing among all the threads
	 * This increases the likelihood of tickling race conditions, if there are any
	 */
	MY_TEST(pthread_barrier_init(&barrier, NULL, NUM_THREADS+1) == 0,
		"Could not init pthread barrier");
	for (int i=0; i<NUM_THREADS; i++) {
		if (i%2 == 0) {
			pthread_create(&thread_ids[i], NULL, pthread_parse_log, (void *) &args);
		} else {
			pthread_create(&thread_ids[i], NULL, pthread_parse_log, (void *) &args2);
		}
	}
	/* Final barrier_wait to set off the thread race */
	barrier_wait_result = pthread_barrier_wait(&barrier);
	MY_TEST(pthread_barrier_ok(barrier_wait_result), "Could not wait on pthread barrier");

	/* Wait for threads to finish parsing the logs */
	for (int i=0; i<NUM_THREADS; i++) {
		MY_TEST(pthread_join(thread_ids[i], (void*) &parsed_logs[i]) == 0, "Could not join thread");
	}

	/* Check that all logs parsed and are equal */
	for (int i=0; i<NUM_THREADS; i++) {
		MY_TEST(parsed_logs[i] != NULL, "Log failed to parse");
		MY_TEST(parsed_logs[i]->version == AA_RECORD_SYNTAX_V2, "Log should have parsed as v2 form");
		MY_TEST(parsed_logs[i]->event == AA_RECORD_DENIED, "Log should have parsed as denied");

		/* Also check i==0 and i==1 as a sanity check for aa_log_record_eq */
		if (i%2 == 0) {
			MY_TEST(aa_log_record_eq(parsed_logs[0], parsed_logs[i]), "Log 0 != Log even");
		} else {
			MY_TEST(aa_log_record_eq(parsed_logs[1], parsed_logs[i]), "Log 1 != Log odd");
		}
	}
	MY_TEST(!aa_log_record_eq(parsed_logs[0], parsed_logs[1]), "Log 0 and log 1 shouldn't be equal");
	/* Clean up */
	MY_TEST(pthread_barrier_destroy(&barrier) == 0, "Could not destroy pthread barrier");
	for (int i=0; i<NUM_THREADS; i++) {
		free_record(parsed_logs[i]);
	}
	return rc;
}