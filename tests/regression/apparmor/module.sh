#! /bin/bash
#Copyright (C) 2021 Canonical, Ltd.
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License as
#published by the Free Software Foundation, version 2 of the
#License.

#=NAME module
#=DESCRIPTION
# This test verifies that the module mediation is working.
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

settest module

test_module_name="module_test"
test_module="$pwd/module_test/$test_module_name.ko"
request_module="$pwd/module_test/request.ko"
extra=/lib/modules/$(uname -r)/kernel/extra

module_cleanup() {
    rm $extra/$test_module_name.ko
    if [ ! "$(ls -A $extra)" ]; then
	rm -r $extra
    fi
    depmod
}
do_onexit="module_cleanup"

mkdir -p $extra
cp $test_module $extra
depmod

do_test()
{
    local desc="MODULE ($1)"
    shift
    runchecktest "$desc" "$@"
}

# Needed for loading module
cap=capability:sys_module

# Ensure it works unconfined
do_test "unconfined load_data" pass "load_data" "$test_module"

do_test "unconfined load_file" pass "load_file" "$test_module"

do_test "unconfined request" pass "request" "$test_module_name"

genprofile "module:load_data" $cap "$test_module:rm"
do_test "module load_data" pass "load_data" "$test_module"

genprofile "module:load_file:$test_module" $cap "$test_module:r"
do_test "module load_file" pass "load_file" "$test_module"

genprofile "module:request:$test_module_name" $cap "module:load_file:$request_module" "$request_module:r"
do_test "module request" pass "request" "$test_module_name"

genprofile $cap "$test_module:rm"
do_test "module load_data fail" fail "load_data" "$test_module"

genprofile $cap "$test_module:r"
do_test "module load_file fail" fail "load_file" "$test_module"

genprofile $cap "module:load_file:$request_module" "$request_module:r"
do_test "module request fail" fail "request" "$test_module_name"

genprofile "module:load_file:$test_module" $cap "$test_module:rm"
do_test "module load_file does not work for load_data" fail "load_data" "$test_module"

genprofile "module:load_data" $cap "$test_module:r"
do_test "module load_data does not work for load_file" fail "load_file" "$test_module"
