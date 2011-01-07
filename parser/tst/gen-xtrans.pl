#!/usr/bin/perl

use strict;
use Locale::gettext;
use POSIX;

setlocale(LC_MESSAGES, "");

my $prefix="simple_tests/generated_x";

my @trans_types = ("p", "P", "c", "C", "u", "i");
my @modifiers = ("i", "u");
my %trans_modifiers = (
    "p" => \@modifiers,
    "P" => \@modifiers,
    "c" => \@modifiers,
    "C" => \@modifiers,
    );

my @targets = ("", "target", "target2");
my @null_target = ("");

my %named_trans = (
    "p" => \@targets,
    "P" => \@targets,
    "c" => \@targets,
    "C" => \@targets,
    "u" => \@null_target,
    "i" => \@null_target,
    );

# audit qualifier disabled for now it really shouldn't affect the conflict
# test but it may be worth checking every once in awhile
#my @qualifiers = ("", "owner", "audit", "audit owner");
my @qualifiers = ("", "owner");

my $count = 0;

gen_conflicting_x();
gen_overlap_re_exact();
gen_dominate_re_re();
gen_ambiguous_re_re();

print "Generated $count xtransition interaction tests\n";

sub gen_list {
    my @output;
    foreach my $trans (@trans_types) {
	if ($trans_modifiers{$trans}) {
	    foreach my $mod (@{$trans_modifiers{$trans}}) {
		push @output, "${trans}${mod}x";
	    }
	}
	push @output, "${trans}x";
    }
    return @output;
}

sub print_rule($$$$) {
    my ($file, $name, $perm, $target) = @_;
    print $file "\t${name} ${perm}";
    if ($target ne "") {
	print $file " -> $target";
    }
    print $file ",\n";
}

sub gen_file($$$$$$$$) {
    my ($name, $xres, $rule1, $perm1, $target1, $rule2, $perm2, $target2) = @_;

#    print "$xres $rule1 $perm1 $target1 $rule2 $perm2 $target2\n";

    my $file;
    unless (open $file, ">$name") {
	print("couldn't open $name\n");
	exit 1;
    }

    print $file "#\n";
    print $file "#=DESCRIPTION ${name}\n";
    print $file "#=EXRESULT ${xres}\n";
    print $file "#\n";
    print $file "/usr/bin/foo {\n";
    print_rule($file, $rule1, $perm1, $target1);
    print_rule($file, $rule2, $perm2, $target2);
    print $file "}";
    close($file);

    $count++;
}

#NOTE: currently we don't do px to cx, or cx to px conversion
#      so
# /foo {
#    /* px -> /foo//bar,
#    /* cx -> bar,
#
# will conflict
#
#NOTE: conflict tests don't tests leading permissions or using unsafe keywords
#      It is assumed that there are extra tests to verify 1 to 1 coorispondance
sub gen_files($$$$) {
    my ($name, $rule1, $rule2, $default) = @_;

    my @perms = gen_list();

#    print "@perms\n";

    foreach my $i (@perms) {
	foreach my $t (@{$named_trans{substr($i, 0, 1)}}) {
	    foreach my $q (@qualifiers) {
		foreach my $j (@perms) {
		    foreach my $u (@{$named_trans{substr($j, 0, 1)}}) {
			foreach my $r (@qualifiers) {
			    my $file="${prefix}/${name}-$q$i$t-$r$j$u.sd";
#		    print "$file\n";

		    #override failures when transitions are the same
			    my $xres = ${default};
			    if ($i eq $j && $t eq $u) {
				$xres = "PASS";
			    }


#		    print "foo $xres $rule1 $i $t $rule2 $j $u\n";
			    gen_file($file, $xres, "$q $rule1", $i, $t, "$r $rule2", $j, $u);
			}
		    }
		}
	    }
	}
    }

}

sub gen_conflicting_x {
    gen_files("conflict", "/bin/cat", "/bin/cat", "FAIL");
}

sub gen_overlap_re_exact {

    gen_files("exact", "/bin/cat", "/bin/*", "PASS");
}

# we currently don't support this, once supported change to "PASS"
sub gen_dominate_re_re {
    gen_files("dominate", "/bin/*", "/bin/**", "FAIL");
}

sub gen_ambiguous_re_re {
    gen_files("ambiguous", "/bin/a*", "/bin/*b", "FAIL");
}
