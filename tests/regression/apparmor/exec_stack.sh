#! /bin/bash
#	Copyright (C) 2016 Canonical, Ltd.
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

#=NAME exec_stack
#=DESCRIPTION
# Verifies basic file access permission checks for a parent profile and a
# stacked subprofile through exec transitions
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. "$bin/prologue.inc"

requires_kernel_features domain/stack
settest transition

file=$tmpdir/file
otherfile=$tmpdir/file2
thirdfile=$tmpdir/file3
sharedfile=$tmpdir/file.shared
okperm=rw

fileok="${file}:${okperm}"
otherok="${otherfile}:${okperm}"
thirdok="${thirdfile}:${okperm}"
sharedok="${sharedfile}:${okperm}"

getcon="/proc/*/attr/{apparmor/,}current:r"

othertest="$pwd/rename"
thirdtest="$pwd/exec"

stackotherok="change_profile->:&$othertest"
stackthirdok="change_profile->:&$thirdtest"

touch $file $otherfile $sharedfile $thirdfile

# We used to do a conditional test (below) for mmap permissions to
# address the change introduced by
# 9f834ec18defc369d73ccf9e87a2790bfa05bf46 but there are too many
# kernels in the wild with a backport/cherrypick of that commit that
# skipped cherry-picking 34c426acb75cc21bdf84685e106db0c1a3565057
# meaning the below conditional check has the wrong results for those
# kernels. Since this test is not about testing mmap just always add
# the mmap perm
#if [ "$(kernel_features domain/fix_binfmt_elf_mmap)" = "true" ]; then
#    elfmmap="m"
#else
#    elfmmap=""
#fi

# Verify file access and contexts by an unconfined process
runchecktest "EXEC_STACK (unconfined - file)" pass -f $file
runchecktest "EXEC_STACK (unconfined - otherfile)" pass -f $otherfile
runchecktest "EXEC_STACK (unconfined - thirdfile)" pass -f $thirdfile
runchecktest "EXEC_STACK (unconfined - sharedfile)" pass -f $sharedfile

runchecktest "EXEC_STACK (unconfined - okcon)" pass -l unconfined -m '(null)'
runchecktest "EXEC_STACK (unconfined - bad label)" fail -l "$test" -m '(null)'
runchecktest "EXEC_STACK (unconfined - bad mode)" fail -l unconfined -m enforce

# Verify file access and contexts by a non-stacked profile
genprofile $fileok $sharedok $getcon
runchecktest "EXEC_STACK (not stacked - file)" pass -f $file
runchecktest_errno EACCES "EXEC_STACK (not stacked - otherfile)" fail -f $otherfile
runchecktest_errno EACCES "EXEC_STACK (not stacked - thirdfile)" fail -f $thirdfile
runchecktest "EXEC_STACK (not stacked - sharedfile)" pass -f $sharedfile

runchecktest "EXEC_STACK (not stacked - okcon)" pass -l "$test" -m enforce
runchecktest "EXEC_STACK (not stacked - bad label)" fail -l "${test}XXX" -m enforce
runchecktest "EXEC_STACK (not stacked - bad mode)" fail -l "$test" -m complain

# Verify file access and contexts by 2 stacked profiles
genprofile -I $fileok $sharedok $getcon $test:"ix -> &$othertest" -- \
	image=$othertest addimage:$test $otherok $sharedok $getcon $test:rm
runchecktest_errno EACCES "EXEC_STACK (2 stacked - file)" fail -- $test -f $file
runchecktest_errno EACCES "EXEC_STACK (2 stacked - otherfile)" fail -- $test -f $otherfile
runchecktest_errno EACCES "EXEC_STACK (2 stacked - thirdfile)" fail -- $test -f $thirdfile
runchecktest "EXEC_STACK (2 stacked - sharedfile)" pass -- $test -f $sharedfile

runchecktest "EXEC_STACK (2 stacked - okcon)" pass -- $test -l "${test}//&${othertest}" -m enforce
runchecktest "EXEC_STACK (2 stacked - bad label)" fail -- $test -l "${test}//&${test}" -m enforce
runchecktest "EXEC_STACK (2 stacked - bad mode)" fail -- $test -l "${test}//&${test}" -m '(null)'

# Verify file access and contexts by 3 stacked profiles
genprofile -I $fileok $sharedok $getcon $test:"ix -> &$othertest" -- \
	image=$othertest addimage:$test $otherok $sharedok $getcon $test:"rix -> &$thirdtest" -- \
	image=$thirdtest addimage:$test $thirdok $sharedok $getcon $test:rm
runchecktest_errno EACCES "EXEC_STACK (3 stacked - file)" fail -- $test -- $test -f $file
runchecktest_errno EACCES "EXEC_STACK (3 stacked - otherfile)" fail -- $test -- $test -f $otherfile
runchecktest_errno EACCES "EXEC_STACK (3 stacked - thirdfile)" fail -- $test -- $test -f $thirdfile
runchecktest "EXEC_STACK (3 stacked - sharedfile)" pass -- $test -- $test -f $sharedfile

runchecktest "EXEC_STACK (3 stacked - okcon)" pass -- $test -- $test -l "${thirdtest}//&${test}//&${othertest}" -m enforce

genprofile -I $sharedok $stackotherok $stackthirdok $test:"rix -> &$othertest" -- \
	image=$othertest addimage:$test $sharedok $stackthirdok $test:"rix -> &$thirdtest" -- \
	image=$thirdtest addimage:$test $sharedok $stackthirdok $test:rm
# Triggered an AppArmor WARN in the initial stacking patch set
runchecktest "EXEC_STACK (3 stacked - old AA WARN)" pass -p $othertest -- $test -p $thirdtest -f $sharedfile

ns="ns"
prof="stackprofile"
nstest=":${ns}:${prof}"
# Verify file access and contexts by stacking a profile with a namespaced profile
genprofile image=$test --stdin <<EOF
$test {
  file,
  audit deny $otherfile $okperm,
  audit deny $thirdfile $okperm,
  $test ix -> &$nstest,
}
EOF

genprofile --append image=$nstest --stdin <<EOF
$nstest {
  file,
  audit deny $file $okperm,
  audit deny $thirdfile $okperm,
}
EOF
runchecktest_errno EACCES "EXEC_STACK (stacked with namespaced profile - file)" fail -- $test -f $file
runchecktest_errno EACCES "EXEC_STACK (stacked with namespaced profile - otherfile)" fail -- $test -f $otherfile
runchecktest_errno EACCES "EXEC_STACK (stacked with namespaced profile - thirdfile)" fail -- $test -f $thirdfile
runchecktest "EXEC_STACK (stacked with namespaced profile - sharedfile)" pass -- $test -f $sharedfile

runchecktest "EXEC_STACK (stacked with namespaced profile - okcon)" pass -- $test -l $prof -m enforce

# Verify file access and contexts in mixed mode
genprofile -I $fileok $sharedok $getcon $test:"ix -> &$othertest" -- \
	image=$othertest flag:complain addimage:$test $otherok $sharedok $getcon $test:rm
runchecktest "EXEC_STACK (mixed mode - file)" pass -- $test -f $file
runchecktest_errno EACCES "EXEC_STACK (mixed mode - otherfile)" fail -- $test -f $otherfile
runchecktest "EXEC_STACK (mixed mode - sharedfile)" pass -- $test -f $sharedfile

runchecktest "EXEC_STACK (mixed mode - okcon)" pass -- $test -l "${othertest}//&${test}" -m mixed

# Verify file access and contexts in complain mode
genprofile -I flag:complain $getcon $test:"ix -> &$othertest" -- \
	image=$othertest flag:complain addimage:$test $getcon
runchecktest "EXEC_STACK (complain mode - file)" pass -- $test -f $file

runchecktest "EXEC_STACK (complain mode - okcon)" pass -- $test -l "${test}//&${othertest}" -m complain
