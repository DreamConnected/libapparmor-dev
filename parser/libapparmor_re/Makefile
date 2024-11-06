# Profiling:
#EXTRA_CFLAGS = -pg

ifdef USE_SYSTEM
  # Using the system libapparmor
  INCLUDE_APPARMOR =
else
  INCLUDE_APPARMOR = -I../../libraries/libapparmor/include
endif

TARGET=libapparmor_re.a

AR ?= ar
CFLAGS ?= -g -Wall -O2 ${EXTRA_CFLAGS} -std=gnu++0x
CXXFLAGS := ${CFLAGS} ${INCLUDE_APPARMOR}

LIB_HDRS = aare_rules.h flex-tables.h apparmor_re.h hfa.h chfa.h parse.h \
	expr-tree.h policy_compat.h

OTHER_HDRS =  ../common_optarg.h ../common_flags.h ../immunix.h \
	../policydb.h ../perms.h ../rule.h

HDRS = ${LIB_HDRS} ${OTHER_HDRS}

ARFLAGS=-rcs

BISON := bison

all : ${TARGET}

UNITTESTS = tst_parse

libapparmor_re.a: parse.o expr-tree.o hfa.o chfa.o aare_rules.o policy_compat.o
	${AR} ${ARFLAGS} $@ $^

expr-tree.o: expr-tree.cc expr-tree.h

hfa.o: hfa.cc ${HDRS}

aare_rules.o: aare_rules.cc ${HDRS}

chfa.o: chfa.cc ${HDRS}

policy_compat.o: policy_compat.cc ${HDRS}

parse.o : parse.cc ${HDRS}

parse.cc : parse.y ${HDRS}
	${BISON} -o $@ $<

clean:
	rm -f *.o parse.cc ${TARGET} *.gcda *.gcno
