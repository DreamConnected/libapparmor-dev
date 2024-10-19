#
#
AUTOMAKE_OPTIONS = foreign
SUBDIRS = libraries/libapparmor  \
	  binutils 		 \
	  parser		 \
	  utils			 \
	  changehat/mod_apparmor \
	  changehat/pam_apparmor \
	  profiles

.PHONY: all
all:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir; \
	done

.PHONY: clean
clean:
	-rm -rf ${RELEASE_DIR} ./apparmor-${VERSION}~* ${COVERITY_DIR}
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir clean; \
	done
