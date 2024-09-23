%module LibAppArmor

%{
#include <aalogparse.h>
#include <sys/apparmor.h>
#include <sys/apparmor_private.h>

%}

%include "typemaps.i"
%include <cstring.i>

%newobject parse_record;
%delobject free_record;
/*
 * Despite its name, %delobject does not hook up destructors to language
 * deletion mechanisms. Instead, it sets flags so that manually calling the
 * free function and then deleting by language mechanisms doesn't cause a
 * double-free.
 *
 * Additionally, we can manually extend the struct with a C++-like
 * destructor. This ensures that the record struct is freed 
 * automatically when the high-level object goes out of scope.
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
#ifdef SWIGPYTHON
%pythonprepend noop_free_record %{
import warnings
warnings.warn("free_record is now a no-op as the record's memory is handled automatically", DeprecationWarning)
%}
#endif
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


/*
 * Map names to preserve backwards compatibility
 */
#ifdef SWIGPYTHON
%rename("_class") aa_log_record::rule_class;
#else
%rename("class") aa_log_record::rule_class;
#endif
%rename("namespace") aa_log_record::aa_namespace;

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

/*
 * label is a heap-allocated pointer, but when label and mode occur together,
 * the freeing of label must be deferred because mode points into label.
 *
 * %cstring_output_allocate((char **label, char **mode), free(*$1))
 * does not handle multi-argument typemaps correctly, so we write our own
 * typemap based on it instead.
 */
%typemap(in,noblock=1,numinputs=0) (char **label, char **mode) ($*1_ltype temp_label = 0, $*2_ltype temp_mode = 0) {
  $1 = &temp_label;
  $2 = &temp_mode;
}
%typemap(freearg,match="in") (char **label, char **mode) ""
%typemap(argout,noblock=1,fragment="SWIG_FromCharPtr") (char **label, char **mode) {
  %append_output(SWIG_FromCharPtr(*$1));
  %append_output(SWIG_FromCharPtr(*$2));
  free(*$1);
}

/*
 * mode is also an out pointer, but it points into an existing buffer.
 * This is a catch-all for occurrences of **mode that aren't paired with **label.
 */
%cstring_output_allocate(char **mode, );

extern char *aa_splitcon(char *con, char **mode);

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

/*
 * aa_is_enabled returns a boolean as an int with failure reason in errno 
 * Therefore, aa_is_enabled either returns True or throws an exception
 *
 * Keep that behavior for backwards compatibilty but return a boolean on Python
 * where it makes more sense, which isn't a breaking change because a boolean is
 * a subclass of int
 */
#ifdef SWIGPYTHON
%typemap(out) int {
	$result = PyBool_FromLong($1);
}
#endif
extern int aa_is_enabled(void);

/* These should not receive the VOID_Object typemap */
extern int aa_change_hat(const char *subprofile, unsigned long magic_token);
extern int aa_change_profile(const char *profile);
extern int aa_change_onexec(const char *profile);
extern int aa_change_hatv(const char *subprofiles[], unsigned long token);
extern int aa_stack_profile(const char *profile);
extern int aa_stack_onexec(const char *profile);

/* aa_find_mountpoint mnt is an output pointer to a heap-allocated string */
%cstring_output_allocate(char **mnt, free(*$1));
/* The other errno-based functions should not always be returning the int value:
 * - Python exceptions signal success/failure status instead via the %exception 
 *   handler above.
 * - Perl (the other binding) has $! for accessing errno but would check the int
 *   return status first.
 *
 * The generated C code for (out) resets the return value to None
 * before appending the returned data (argout generated by %cstring stuff)
 */
#ifdef SWIGPYTHON
%typemap(out,noblock=1) int {
#if defined(VOID_Object)
	$result = VOID_Object;
#endif
}
#endif
extern int aa_find_mountpoint(char **mnt);
extern int aa_getprocattr(pid_t tid, const char *attr, char **label, char **mode);
extern int aa_gettaskcon(pid_t target, char **label, char **mode);
extern int aa_getcon(char **label, char **mode);
extern int aa_getpeercon(int fd, char **label, char **mode);
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
