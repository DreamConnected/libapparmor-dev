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
from apparmor.regex import RE_PROFILE_SIGNAL, RE_PROFILE_NAME
from apparmor.rule import (
    BaseRule, BaseRuleset, check_and_split_list, logprof_value_or_all,
    parse_modifiers, quote_if_needed)
from apparmor.translations import init_translation

_ = init_translation()

access_keywords_read = ['receive', 'r', 'read']
access_keywords_write = ['send', 'w', 'write']
access_keywords_rw = ['rw', 'wr']
access_keywords = access_keywords_read + access_keywords_write + access_keywords_rw

signal_keywords = [
    'hup', 'int', 'quit', 'ill', 'trap', 'abrt', 'bus', 'fpe', 'kill', 'usr1',
    'segv', 'usr2', 'pipe', 'alrm', 'term', 'stkflt', 'chld', 'cont', 'stop',
    'stp', 'ttin', 'ttou', 'urg', 'xcpu', 'xfsz', 'vtalrm', 'prof', 'winch',
    'io', 'pwr', 'sys', 'emt', 'exists']
RE_SIGNAL_REALTIME = re.compile(r'^rtmin\+0*([0-9]|[12][0-9]|3[0-2])$')  # rtmin+0..rtmin+32, number may have leading zeros

joint_access_keyword = r'\s*(' + '|'.join(access_keywords) + r')\s*'
RE_ACCESS_KEYWORDS = (
    joint_access_keyword  # one of the access_keyword
    + '|'  # or
    + r'\(' + joint_access_keyword + '(' + r'(\s|,)+' + joint_access_keyword + ')*' + r'\)'  # one or more access_keyword in (...)
)

signal_keyword = r'\s*([a-z0-9+]+|"[a-z0-9+]+")\s*'  # don't check against the signal keyword list in the regex to allow a more helpful error message
RE_SIGNAL_KEYWORDS = (
    r'set\s*=\s*' + signal_keyword  # one of the signal_keyword
    + '|'  # or
    + r'set\s*=\s*\(' + signal_keyword + '(' + r'(\s|,)+' + signal_keyword + ')*' + r'\)'  # one or more signal_keyword in (...)
)


RE_SIGNAL_DETAILS = re.compile(
    '^'
    + r'(\s+(?P<access>' + RE_ACCESS_KEYWORDS + '))?'  # optional access keyword(s)
    + '(?P<signal>' + r'(\s+(' + RE_SIGNAL_KEYWORDS + '))+' + ')?'  # optional signal set(s)
    + r'(\s+(peer=' + RE_PROFILE_NAME % 'peer' + '))?'  # optional peer
    + r'\s*$')


RE_FILTER_SET_1 = re.compile(r'set\s*=\s*\(([^)]*)\)')
RE_FILTER_SET_2 = re.compile(r'set\s*=')
RE_FILTER_PARENTHESIS = re.compile(r'\((.*)\)')
RE_FILTER_QUOTES = re.compile('"([a-z0-9]+)"')  # used to strip quotes around signal keywords - don't use for peer!


class SignalRule(BaseRule):
    """Class to handle and store a single signal rule"""

    # Nothing external should reference this class, all external users
    # should reference the class field SignalRule.ALL
    class __SignalAll:
        pass

    ALL = __SignalAll

    rule_name = 'signal'
    _match_re = RE_PROFILE_SIGNAL

    def __init__(self, access, signal, peer, audit=False, deny=False, allow_keyword=False,
                 comment='', log_event=None, priority=None):

        super().__init__(audit=audit, deny=deny, allow_keyword=allow_keyword,
                         comment=comment, log_event=log_event, priority=priority)

        self.access, self.all_access, unknown_items = check_and_split_list(
            access, access_keywords, self.ALL, type(self).__name__, 'access')
        if unknown_items:
            raise AppArmorException(_('Passed unknown access keyword to %s: %s') % (type(self).__name__, ' '.join(unknown_items)))

        self.signal, self.all_signals, unknown_items = check_and_split_list(
            signal, signal_keywords, self.ALL, type(self).__name__, 'signal')
        if unknown_items:
            for item in unknown_items:
                if RE_SIGNAL_REALTIME.match(item):
                    self.signal.add(item)
                else:
                    raise AppArmorException(_('Passed unknown signal keyword to %s: %s') % (type(self).__name__, item))

        self.peer, self.all_peers = self._aare_or_all(peer, 'peer', is_path=False, log_event=log_event)

    @classmethod
    def _create_instance(cls, raw_rule, matches):
        """parse raw_rule and return instance of this class"""

        priority, audit, deny, allow_keyword, comment = parse_modifiers(matches)

        rule_details = ''
        if matches.group('details'):
            rule_details = matches.group('details')

        if rule_details:
            details = RE_SIGNAL_DETAILS.search(rule_details)
            if not details:
                raise AppArmorException(_("Invalid or unknown keywords in 'signal %s" % rule_details))

            if details.group('access'):
                access = details.group('access')
                if access.startswith('(') and access.endswith(')'):
                    access = access[1:-1]
                access = access.replace(',', ' ').split()  # split by ',' or whitespace
            else:
                access = cls.ALL

            if details.group('signal'):
                signal = details.group('signal')
                signal = RE_FILTER_SET_1.sub(r'\1', signal)  # filter out 'set='
                signal = RE_FILTER_SET_2.sub('', signal)  # filter out 'set='
                signal = RE_FILTER_QUOTES.sub(r' \1 ', signal)  # filter out quote pairs
                signal = signal.replace(',', ' ').split()  # split at ',' or whitespace
            else:
                signal = cls.ALL

            if details.group('peer'):
                peer = details.group('peer')
            else:
                peer = cls.ALL
        else:
            access = cls.ALL
            signal = cls.ALL
            peer = cls.ALL

        return cls(access, signal, peer,
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
            raise AppArmorBug('Empty access in signal rule')

        if self.all_signals:
            signal = ''
        elif len(self.signal) == 1:
            signal = ' set=%s' % ' '.join(self.signal)
        elif self.signal:
            signal = ' set=(%s)' % ' '.join(sorted(self.signal))
        else:
            raise AppArmorBug('Empty signal in signal rule')

        if self.all_peers:
            peer = ''
        elif self.peer:
            peer = ' peer=%s' % quote_if_needed(self.peer.regex)
        else:
            raise AppArmorBug('Empty peer in signal rule')

        return ('%s%ssignal%s%s%s,%s' % (space, self.modifiers_str(), access, signal, peer, self.comment))

    def _is_covered_localvars(self, other_rule):
        """check if other_rule is covered by this rule object"""

        if not self._is_covered_list(self.access, self.all_access, other_rule.access, other_rule.all_access, 'access'):
            return False

        if not self._is_covered_list(self.signal, self.all_signals, other_rule.signal, other_rule.all_signals, 'signal'):
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

        if (self.signal != rule_obj.signal
                or self.all_signals != rule_obj.all_signals):
            return False

        if not self._is_equal_aare(self.peer, self.all_peers, rule_obj.peer, rule_obj.all_peers, 'peer'):
            return False

        return True

    def _logprof_header_localvars(self):
        access = logprof_value_or_all(self.access, self.all_access)
        signal = logprof_value_or_all(self.signal, self.all_signals)
        peer   = logprof_value_or_all(self.peer,   self.all_peers)  # noqa: E221

        return (
            _('Access mode'), access,
            _('Signal'), signal,
            _('Peer'), peer,
        )

    @staticmethod
    def hashlog_from_event(hl, e):
        hl[e['peer']][e['denied_mask']][e['signal']] = True

    @classmethod
    def from_hashlog(cls, hl):
        for peer in hl.keys():
            if '//null-' in peer:
                continue  # ignore null-* peers

            for access, signal in BaseRule.generate_rules_from_hashlog(hl[peer], 2):
                yield cls(access, signal, peer, log_event=True)


class SignalRuleset(BaseRuleset):
    """Class to handle and store a collection of signal rules"""

    def get_glob(self, path_or_rule):
        """Return the next possible glob. For signal rules, that means removing access, signal or peer"""
        # XXX only remove one part, not all
        return 'signal,'
