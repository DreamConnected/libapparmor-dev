# ----------------------------------------------------------------------
#    Copyright (C) 2015 Christian Boltz <apparmor@cboltz.de>
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of version 2 of the GNU General Public
#    License as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
# ----------------------------------------------------------------------

import re

from apparmor.common import AppArmorBug, AppArmorException
from apparmor.regex import RE_PROFILE_PTRACE, RE_PROFILE_NAME, strip_quotes
from apparmor.rule import (
    BaseRule, BaseRuleset, check_and_split_list, logprof_value_or_all,
    parse_modifiers, quote_if_needed)
from apparmor.translations import init_translation

_ = init_translation()

access_keywords = ['r', 'w', 'rw', 'wr', 'read', 'write', 'readby', 'trace', 'tracedby']  # XXX 'wr' and 'write' accepted by the parser, but not documented in apparmor.d.pod

# XXX joint_access_keyword and RE_ACCESS_KEYWORDS exactly as in PtraceRule - move to function!
joint_access_keyword = r'\s*(' + '|'.join(access_keywords) + r')\s*'
RE_ACCESS_KEYWORDS = (joint_access_keyword  # one of the access_keyword
                      + '|'  # or
                      + r'\(' + joint_access_keyword + '(' + r'(\s|,)+' + joint_access_keyword + ')*' + r'\)')  # one or more access_keyword in (...)


RE_PTRACE_DETAILS = re.compile(
    '^'
    + r'(\s+(?P<access>' + RE_ACCESS_KEYWORDS + '))?'  # optional access keyword(s)
    + r'(\s+(peer=' + RE_PROFILE_NAME % 'peer' + '))?'  # optional peer
    + r'\s*$')


class PtraceRule(BaseRule):
    """Class to handle and store a single ptrace rule"""

    # Nothing external should reference this class, all external users
    # should reference the class field PtraceRule.ALL
    class __PtraceAll:
        pass

    ALL = __PtraceAll

    rule_name = 'ptrace'
    _match_re = RE_PROFILE_PTRACE

    def __init__(self, access, peer, audit=False, deny=False, allow_keyword=False,
                 comment='', log_event=None, priority=None):

        super().__init__(audit=audit, deny=deny, allow_keyword=allow_keyword,
                         comment=comment, log_event=log_event, priority=priority)

        self.access, self.all_access, unknown_items = check_and_split_list(
            access, access_keywords, self.ALL, type(self).__name__, 'access')
        if unknown_items:
            raise AppArmorException(_('Passed unknown access keyword to %s: %s') % (type(self).__name__, ' '.join(unknown_items)))

        self.peer, self.all_peers = self._aare_or_all(peer, 'peer', is_path=False, log_event=log_event)

    @classmethod
    def _create_instance(cls, raw_rule, matches):
        """parse raw_rule and return instance of this class"""

        priority, audit, deny, allow_keyword, comment = parse_modifiers(matches)

        rule_details = ''
        if matches.group('details'):
            rule_details = matches.group('details')

        if rule_details:
            details = RE_PTRACE_DETAILS.search(rule_details)
            if not details:
                raise AppArmorException(_("Invalid or unknown keywords in 'ptrace %s" % rule_details))

            if details.group('access'):
                # XXX move to function _split_access()?
                access = details.group('access')
                if access.startswith('(') and access.endswith(')'):
                    access = access[1:-1]
                access = access.replace(',', ' ').split()  # split by ',' or whitespace
            else:
                access = cls.ALL

            if details.group('peer'):
                peer = strip_quotes(details.group('peer'))
            else:
                peer = cls.ALL
        else:
            access = cls.ALL
            peer = cls.ALL

        return cls(access, peer,
                   audit=audit, deny=deny, allow_keyword=allow_keyword, comment=comment, priority=priority)

    def get_clean(self, depth=0):
        """return rule (in clean/default formatting)"""

        space = '  ' * depth

        if self.all_access:
            access = ''
        elif len(self.access) == 1:
            access = ' %s' % ' '.join(self.access)
        elif self.access:
            access = ' (%s)' % ' '.join(sorted(self.access))
        else:
            raise AppArmorBug('Empty access in ptrace rule')

        if self.all_peers:
            peer = ''
        elif self.peer:
            peer = ' peer=%s' % quote_if_needed(self.peer.regex)
        else:
            raise AppArmorBug('Empty peer in ptrace rule')

        return ('%s%sptrace%s%s,%s' % (space, self.modifiers_str(), access, peer, self.comment))

    def _is_covered_localvars(self, other_rule):
        """check if other_rule is covered by this rule object"""

        if not self._is_covered_list(self.access, self.all_access, other_rule.access, other_rule.all_access, 'access'):
            return False

        if not self._is_covered_aare(self.peer, self.all_peers, other_rule.peer, other_rule.all_peers, 'peer'):
            return False

        # still here? -> then it is covered
        return True

    def _is_equal_localvars(self, rule_obj, strict):
        """compare if rule-specific variables are equal"""

        if (self.access != rule_obj.access
                or self.all_access != rule_obj.all_access):
            return False

        if not self._is_equal_aare(self.peer, self.all_peers, rule_obj.peer, rule_obj.all_peers, 'peer'):
            return False

        return True

    def _logprof_header_localvars(self):
        access = logprof_value_or_all(self.access, self.all_access)
        peer   = logprof_value_or_all(self.peer,   self.all_peers)  # noqa: E221

        return (
            _('Access mode'), access,
            _('Peer'), peer,
        )

    @staticmethod
    def hashlog_from_event(hl, e):
        hl[e['peer']][e['denied_mask']] = True

    @classmethod
    def from_hashlog(cls, hl):
        for peer in hl.keys():
            if '//null-' in peer:
                continue  # ignore null-* peers

            for access in hl[peer].keys():
                yield cls(access, peer, log_event=True)


class PtraceRuleset(BaseRuleset):
    """Class to handle and store a collection of ptrace rules"""

    def get_glob(self, path_or_rule):
        """Return the next possible glob. For ptrace rules, that means removing access or removing/globbing peer"""
        # XXX only remove one part, not all
        return 'ptrace,'
