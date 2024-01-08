#! /bin/bash
#Copyright (C) 2022 Canonical, Ltd.
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License as
#published by the Free Software Foundation, version 2 of the
#License.

#=NAME posix_mq
#=DESCRIPTION
# This test verifies if mediation of posix message queues is working
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

#requires_kernel_features network_v8/finegrained
requires_parser_support "network ip=::1,"

settest net_finegrained_rcv

sender="$bin/net_finegrained_snd"
receiver="$bin/net_finegrained_rcv"

# local ipv6 address generated according to https://www.rfc-editor.org/rfc/rfc4193.html
#ipv6_subnet=fd74:1820:b03a:b361::/64
bind_ipv6=fd74:1820:b03a:b361::cf32
remote_ipv6=fd74:1820:b03a:b361::a0f9

bind_ipv4=127.0.97.3
remote_ipv4=127.187.243.54

ip -6 addr add $bind_ipv6 dev lo || true
ip -6 addr add $remote_ipv6 dev lo || true

cleanup()
{
	ip -6 addr del $bind_ipv6 dev lo || true
	ip -6 addr del $remote_ipv6 dev lo || true
}

do_onexit="cleanup"

do_test()
{
	local desc="FINEGRAINED NETWORK ($1)"
	shift
	runchecktest "$desc" "$@"
}


do_tests()
{
	prefix="$1"
	expect_rcv=$2
	expect_snd=$3
	bind_ip=$4
	bind_port=$5
	remote_ip=$6
	remote_port=$7
	protocol=$8
	generate_profile=$9

	settest net_finegrained_rcv
	$generate_profile
	do_test "$prefix - root" $expect_rcv --bind_ip $bind_ip --bind_port $bind_port --remote_ip $remote_ip --remote_port $remote_port --protocol $protocol --timeout 5 --sender $sender


	settest -u "foo" net_finegrained_rcv
	$generate_profile
	do_test "$prefix - user" $expect_rcv --bind_ip $bind_ip --bind_port $bind_port --remote_ip $remote_ip --remote_port $remote_port --protocol $protocol --timeout 5 --sender $sender


}

bind_port=3456
while lsof -i:$bind_port >/dev/null; do
	let bind_port=$bind_port+1
done

let remote_port=$bind_port+1
while lsof -i:$remote_port >/dev/null; do
	let remote_port=$remote_port+1
done

generate_profile=""
do_tests "ipv4 udp unconfined" pass pass $bind_ipv4 $bind_port $remote_ipv4 $remote_port udp "$generate_profile"
do_tests "ipv4 tcp unconfined" pass pass $bind_ipv4 $bind_port $remote_ipv4 $remote_port tcp "$generate_profile"

generate_profile="genprofile network;ip=$bind_ipv4;port=$bind_port;peer=(ip=$remote_ipv4,port=$remote_port) $sender:px -- image=$sender network;ip=$remote_ipv4;port=$remote_port;peer=(ip=$bind_ipv4,port=$bind_port)"
do_tests "ipv4 udp generic perms" pass pass $bind_ipv4 $bind_port $remote_ipv4 $remote_port udp "$generate_profile"

generate_profile="genprofile network;ip=$bind_ipv4;port=$bind_port;peer=(ip=$remote_ipv4,port=$remote_port) $sender:px -- image=$sender network;ip=$remote_ipv4;port=$remote_port;peer=(ip=$bind_ipv4,port=$bind_port)"
do_tests "ipv4 tcp generic perms" pass pass $bind_ipv4 $bind_port $remote_ipv4 $remote_port tcp "$generate_profile"

generate_profile="genprofile network;(connect,receive,send);ip=$bind_ipv4;port=$bind_port;peer=(ip=$remote_ipv4,port=$remote_port) $sender:px -- image=$sender network;ip=$remote_ipv4;port=$remote_port;peer=(ip=$bind_ipv4,port=$bind_port)"
do_tests "ipv4 udp generic perms" pass pass $bind_ipv4 $bind_port $remote_ipv4 $remote_port udp "$generate_profile"

generate_profile="genprofile network;ip=$bind_ipv4;port=$bind_port;peer=(ip=$remote_ipv4,port=$remote_port) $sender:px -- image=$sender network;ip=$remote_ipv4;port=$remote_port;peer=(ip=$bind_ipv4,port=$bind_port)"
do_tests "ipv4 tcp generic perms" pass pass $bind_ipv4 $bind_port $remote_ipv4 $remote_port tcp "$generate_profile"

removeprofile
# ipv6 tests

generate_profile=""
do_tests "ipv6 udp unconfined" pass pass $bind_ipv6 $bind_port $remote_ipv6 $remote_port udp "$generate_profile"
do_tests "ipv6 tcp unconfined" pass pass $bind_ipv6 $bind_port $remote_ipv6 $remote_port tcp "$generate_profile"

generate_profile="genprofile network;ip=$bind_ipv6;port=$bind_port;peer=(ip=$remote_ipv6,port=$remote_port) $sender:px -- image=$sender network;ip=$remote_ipv6;port=$remote_port;peer=(ip=$bind_ipv6,port=$bind_port)"
do_tests "ipv6 udp generic perms" pass pass $bind_ipv6 $bind_port $remote_ipv6 $remote_port udp "$generate_profile"

generate_profile="genprofile network;ip=$bind_ipv6;port=$bind_port;peer=(ip=$remote_ipv6,port=$remote_port) $sender:px -- image=$sender network;ip=$remote_ipv6;port=$remote_port;peer=(ip=$bind_ipv6,port=$bind_port)"
do_tests "ipv6 tcp generic perms" pass pass $bind_ipv6 $bind_port $remote_ipv6 $remote_port tcp "$generate_profile"


