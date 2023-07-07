# ----------------------------------------------------------------------
#    Copyright (C) 2021 Canonical, Ltd.
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

from apparmor.regex import RE_PROFILE_MODULE, RE_PROFILE_NAME, strip_quotes
from apparmor.common import AppArmorBug, AppArmorException
from apparmor.rule import BaseRule, BaseRuleset, check_and_split_list, logprof_value_or_all, parse_modifiers, quote_if_needed

# setup module translations
from apparmor.translations import init_translation
_ = init_translation()

mode_keywords = ['load_data', 'load_file', 'request']

RE_MODE_KEYWORDS = ('(' + '|'.join(mode_keywords) + ')')

RE_MODULE_DETAILS  = re.compile(
    '^' +
    r'(\s+(?P<mode>' + RE_MODE_KEYWORDS + '))' +
    r'(\s+(' + RE_PROFILE_NAME % 'target'  + '))?' + # optional target
    r'\s*$')


class ModuleRule(BaseRule):
    '''Class to handle and store a single module rule'''

    # Nothing external should reference this class, all external users
    # should reference the class field ModuleRule.ALL
    class __ModuleAll:
        pass

    ALL = __ModuleAll

    rule_name = 'module'
    _match_re = RE_PROFILE_MODULE

    def __init__(self, mode, target, audit=False, deny=False, allow_keyword=False,
                 comment='', log_event=None):

        super().__init__(audit=audit, deny=deny,
                         allow_keyword=allow_keyword,
                         comment=comment,
                         log_event=log_event)

        self.mode, self.all_mode, unknown_items = check_and_split_list(mode, mode_keywords, self.ALL, type(self).__name__, 'mode')
        if unknown_items:
            raise AppArmorException(('Passed unknown mode keyword to %s: %s') % (type(self).__name__, ' '.join(unknown_items)))
        if self.mode and len(self.mode) > 1:
            raise AppArmorException(('Passed more than one mode keyword to %s') % type(self).__name__)

        self.target, self.all_target = self._aare_or_all(target, 'target', is_path=False, log_event=log_event)

        if self.target and 'load_data' in self.mode:
            raise AppArmorException('Target cannot be used with load_data')

    @classmethod
    def _create_instance(cls, raw_rule, matches):
        '''parse raw_rule and return instance of this class'''

        audit, deny, allow_keyword, comment = parse_modifiers(matches)

        rule_details = ''
        if matches.group('details'):
            rule_details = matches.group('details')

        if rule_details:
            details = RE_MODULE_DETAILS.search(rule_details)
            if not details:
                raise AppArmorException(_("Invalid or unknown keywords in 'module %s" % rule_details))

            mode = details.group('mode')

            if details.group('target'):
                if mode == 'load_data':
                    raise AppArmorException(_("load_data does not support target"))
                target = strip_quotes(details.group('target'))
            else:
                if mode != 'load_data':
                    raise AppArmorException(_("Target must be specified for mode %s" % mode))
                target = cls.ALL
        else:
            mode = cls.ALL
            target = cls.ALL

        return cls(mode, target, audit=audit, deny=deny,
                   allow_keyword=allow_keyword, comment=comment)

    def get_clean(self, depth=0):
        '''return rule (in clean/default formatting)'''

        space = '  ' * depth

        if self.all_mode:
            mode = ''
        elif self.mode:
            mode = ' %s' % ''.join(self.mode)
        else:
            raise AppArmorBug('Empty mode in module rule')

        if self.all_target:
            target = ''
        elif self.target:
            target = ' %s' % quote_if_needed(self.target.regex)
        else:
            raise AppArmorBug('Empty target in module rule')

        return('%s%smodule%s%s,%s' % (space, self.modifiers_str(), mode, target, self.comment))

    def _is_covered_localvars(self, other_rule):
        '''check if other_rule is covered by this rule object'''

        if not self._is_covered_plain(self.mode, self.all_mode, other_rule.mode, other_rule.all_mode, 'mode'):
            return False

        if not self._is_covered_aare(self.target, self.all_target, other_rule.target, other_rule.all_target, 'target'):
            return False

        # still here? -> then it is covered
        return True

    def _is_equal_localvars(self, rule_obj, strict):
        '''compare if rule-specific variables are equal'''

        if (self.mode != rule_obj.mode or
            self.all_mode != rule_obj.all_mode):
            return False

        if not self._is_equal_aare(self.target, self.all_target, rule_obj.target, rule_obj.all_target, 'target'):
            return False

        return True

    def _logprof_header_localvars(self):
        mode   = logprof_value_or_all(self.mode, self.all_mode)
        target = logprof_value_or_all(self.target, self.all_target)

        return [
            _('Mode'), mode,
            _('Target'), target
        ]


class ModuleRuleset(BaseRuleset):
    '''Class to handle and store a collection of module rules'''

    def get_glob(self, path_or_rule):
        '''Return the next possible glob. For mqueue rules, that means removing mode and target'''
        return 'module,'
