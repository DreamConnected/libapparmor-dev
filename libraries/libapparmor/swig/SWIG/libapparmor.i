%module LibAppArmor

%{
#include <aalogparse.h>
#include <sys/apparmor.h>
#include <sys/apparmor_private.h>

%}

%include "typemaps.i"

%newobject parse_record;
%delobject free_record;
/*
 * Despite its name, %delobject does not hook up destructors to language
 * deletion mechanisms. Instead, it sets flags so that manually calling the
 * free function and then deleting by language mechanisms doesn't cause a
 * double-free.
 *
 * Instead, we need manually extend the struct with a C++-like destructor.
 * This ensures that the record struct is free when the high-level object
 * goes out of scope.
 */
%extend aa_log_record {
	~aa_log_record() {
		free_record($self);
	}
}

/*
 * Generate a no-op free_record wrapper to avoid making a double-free footgun.
 * Use rename directive to avoid colliding with the actual free_record, which
 * we use above to clean up when the higher-level language deletes the object.
 * 
 * Ideally we would not expose a free_record at all, but we need to maintain
 * backwards compatibility with the existing high-level code that uses it.
 */
%rename(free_record) noop_free_record;
%feature("autodoc",
  "This function used to free aa_log_record objects. Freeing is now handled "
  "automatically, so this no-op function remains for backwards compatibility.") noop_free_record;
%inline %{
  void noop_free_record(aa_log_record *record) {(void) record;}
%}

/*
 * Do not autogenerate a wrapper around free_record. This does not prevent us
 * from calling it ourselves in %extend C code.
 */
%ignore free_record;

%include <aalogparse.h>

/**
 * swig doesn't like the macro magic we do in apparmor.h and apparmor_private.h
 * so the function prototypes must be manually inserted.
 *
 * Functions that return a negative int and set errno upon error use a special
 * %exception directive and must be listed after the %exception below. All
 * other functions go here.
 */

/* apparmor.h */

extern char *aa_splitcon(char *con, char **mode);

/* apparmor_private.h */

extern int _aa_is_blacklisted(const char *name);

#ifdef SWIGPYTHON
%exception {
  $action
  if (result < 0) {
    // Unfortunately SWIG_exception does not support OSError
    PyErr_SetFromErrno(PyExc_OSError);
    SWIG_fail;
  }
}
#endif

/* Functions that return a negative int and set errno upon error go here. */

/* apparmor.h */

extern int aa_is_enabled(void);
extern int aa_find_mountpoint(char **mnt);
extern int aa_change_hat(const char *subprofile, unsigned long magic_token);
extern int aa_change_profile(const char *profile);
extern int aa_change_onexec(const char *profile);
extern int aa_change_hatv(const char *subprofiles[], unsigned long token);
extern int aa_change_hat_vargs(unsigned long token, int count, ...);
extern int aa_stack_profile(const char *profile);
extern int aa_stack_onexec(const char *profile);
extern int aa_getprocattr_raw(pid_t tid, const char *attr, char *buf, int len,
			      char **mode);
extern int aa_getprocattr(pid_t tid, const char *attr, char **label, char **mode);
extern int aa_gettaskcon(pid_t target, char **label, char **mode);
extern int aa_getcon(char **label, char **mode);
extern int aa_getpeercon_raw(int fd, char *buf, socklen_t *len, char **mode);
extern int aa_getpeercon(int fd, char **label, char **mode);
extern int aa_query_label(uint32_t mask, char *query, size_t size, int *allowed,
			  int *audited);
extern int aa_query_file_path_len(uint32_t mask, const char *label,
				  size_t label_len, const char *path,
				  size_t path_len, int *allowed, int *audited);
extern int aa_query_file_path(uint32_t mask, const char *label,
			      const char *path, int *allowed, int *audited);
extern int aa_query_link_path_len(const char *label, size_t label_len,
				  const char *target, size_t target_len,
				  const char *link, size_t link_len,
				  int *allowed, int *audited);
extern int aa_query_link_path(const char *label, const char *target,
			      const char *link, int *allowed, int *audited);

%exception;
