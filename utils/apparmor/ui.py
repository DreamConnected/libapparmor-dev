# ----------------------------------------------------------------------
#    Copyright (C) 2013 Kshitij Gupta <kgupta8592@gmail.com>
#    Copyright (C) 2017 Christian Boltz <apparmor@cboltz.de>
#    Copyright (C) 2017 SUSE Linux
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

import json
import os
import re
import readline
import subprocess
import sys
from tempfile import NamedTemporaryFile

from apparmor.common import AppArmorException, DebugLogger, readkey
from apparmor.translations import init_translation

_ = init_translation()

# Set up UI logger for separate messages from UI module
debug_logger = DebugLogger('UI')

ARROWS = {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}

UI_mode = 'text'
jsonlog = None


def write_json(jsonout):
    jtxt = json.dumps(jsonout, sort_keys=False, separators=(',', ': '))

    if jsonlog:
        jsonlog.write('o ' + jtxt + '\n')

    print(jtxt)
    sys.stdout.flush()


def set_json_mode(cfg):
    """
    Currently this is only used by aa-genprof and aa-logprof, while e.g.
    aa-status generates its own JSON output.

    Remember to bump the JSON API version number if the output commands
    in this file are modified.

    Current known consumers of the JSON output:
    - YaST

    The cfg parameter expects the parsed logprof.conf aka apparmor.aa.cfg.
    """
    global UI_mode, jsonlog

    if int(cfg['settings'].get('json_log', False)):
        jsonlog = NamedTemporaryFile('w', prefix='aa-jsonlog-', delete=False, encoding='utf-8')

    UI_mode = 'json'
    jsonout = {'dialog': 'apparmor-json-version', 'data': '2.12'}
    write_json(jsonout)


def set_text_mode():
    """Output plaintext"""
    global UI_mode
    UI_mode = 'text'


def set_allow_all_mode():
    global UI_mode
    UI_mode = 'allow_all'


# reads the response on command line for json and verifies the response
# for the dialog type
def json_response(dialog_type):
    string = input('\n')

    if jsonlog:
        jsonlog.write('i ' + string + '\n')

    rh = json.loads(string.strip())
    if rh["dialog"] != dialog_type:
        raise AppArmorException('Expected response %s got %s.' % (dialog_type, string))
    return rh


def getkey():
    key = readkey()
    if key == '\x1B':
        key = readkey()
        if key == '[':
            key = readkey()
            if ARROWS.get(key, False):
                key = ARROWS[key]
    return key.strip()


def UI_Info(text):
    """Facility to output normal text"""
    debug_logger.info(text)
    if UI_mode == 'json':
        jsonout = {'dialog': 'info', 'data': text}
        write_json(jsonout)
    else:  # text mode
        sys.stdout.write(text + '\n')


def UI_Important(text):
    """Facility to output important text"""
    debug_logger.debug(text)
    if UI_mode == 'json':
        jsonout = {'dialog': 'important', 'data': text}
        write_json(jsonout)
    else:  # text mode
        sys.stdout.write('\n' + text + '\n')


def get_translated_hotkey(translated, cmsg=''):
    # Originally (\S) was used but with translations it would not work :(
    match = re.search(r'\((\S+)\)', translated)
    if match:
        return match.groups()[0].lower()

    if not cmsg:
        cmsg = 'PromptUser: %s %s' % (_('Invalid hotkey for'), translated)
    raise AppArmorException(cmsg)


def UI_YesNo(text, default):
    debug_logger.debug('UI_YesNo: %s: %s %s', UI_mode, text, default)
    default = default.lower()
    yes = CMDS['CMD_YES']
    no = CMDS['CMD_NO']
    yeskey = get_translated_hotkey(yes)
    nokey = get_translated_hotkey(no)
    ans = 'XXXINVALIDXXX'
    while ans not in ('y', 'n'):
        if UI_mode == 'json':
            jsonout = {'dialog': 'yesno', 'text': text, 'default': default}
            write_json(jsonout)
            hm = json_response('yesno')
            ans = hm['response_key']
        else:  # text mode
            sys.stdout.write('\n' + text + '\n')
            if default == 'y':
                sys.stdout.write('\n[%s] / %s\n' % (yes, no))
            else:
                sys.stdout.write('\n%s / [%s]\n' % (yes, no))
            if UI_mode == 'allow_all':
                ans = nokey
            else:
                ans = getkey()
            if ans:
                # Get back to english from localised answer
                ans = ans.lower()
                if ans == yeskey:
                    ans = 'y'
                elif ans == nokey:
                    ans = 'n'
                elif ans == 'left':
                    default = 'y'
                elif ans == 'right':
                    default = 'n'
                else:
                    ans = 'XXXINVALIDXXX'
                    continue  # If user presses any other button ask again
            else:
                ans = default
    return ans


def UI_YesNoCancel(text, default):
    debug_logger.debug('UI_YesNoCancel: %s: %s %s', UI_mode, text, default)
    default = default.lower()
    yes = CMDS['CMD_YES']
    no = CMDS['CMD_NO']
    cancel = CMDS['CMD_CANCEL']

    yeskey = get_translated_hotkey(yes)
    nokey = get_translated_hotkey(no)
    cancelkey = get_translated_hotkey(cancel)

    ans = 'XXXINVALIDXXX'
    while ans not in ('c', 'n', 'y'):
        if UI_mode == 'json':
            jsonout = {'dialog': 'yesnocancel', 'text': text, 'default': default}
            write_json(jsonout)
            hm = json_response('yesnocancel')
            ans = hm['response_key']
        else:  # text mode
            sys.stdout.write('\n' + text + '\n')
            if default == 'y':
                sys.stdout.write('\n[%s] / %s / %s\n' % (yes, no, cancel))
            elif default == 'n':
                sys.stdout.write('\n%s / [%s] / %s\n' % (yes, no, cancel))
            else:
                sys.stdout.write('\n%s / %s / [%s]\n' % (yes, no, cancel))
            if UI_mode == 'allow_all':
                ans = nokey
            else:
                ans = getkey()
            if ans:
                # Get back to english from localised answer
                ans = ans.lower()
                if ans == yeskey:
                    ans = 'y'
                elif ans == nokey:
                    ans = 'n'
                elif ans == cancelkey:
                    ans = 'c'
                elif ans == 'left':
                    if default == 'n':
                        default = 'y'
                    elif default == 'c':
                        default = 'n'
                elif ans == 'right':
                    if default == 'y':
                        default = 'n'
                    elif default == 'n':
                        default = 'c'
            else:
                ans = default
    return ans


def UI_GetString(text, default):
    debug_logger.debug('UI_GetString: %s: %s %s', UI_mode, text, default)
    string = default
    if UI_mode == 'json':
        jsonout = {'dialog': 'getstring', 'text': text, 'default': default}
        write_json(jsonout)
        string = json_response('getstring')["response"]
    else:  # text mode
        readline.set_startup_hook(lambda: readline.insert_text(default))
        try:
            string = input('\n' + text)
        except EOFError:
            string = ''
        finally:
            readline.set_startup_hook()
    return string.strip()


def UI_GetFile(file):
    debug_logger.debug('UI_GetFile: %s', UI_mode)
    filename = None
    if UI_mode == 'json':
        jsonout = {'dialog': 'getfile', 'text': file['description']}
        write_json(jsonout)
        filename = json_response('getfile')["response"]
    else:  # text mode
        sys.stdout.write(file['description'] + '\n')
        filename = sys.stdin.read()
    return filename


def UI_BusyStart(message):
    debug_logger.debug('UI_BusyStart: %s', UI_mode)
    UI_Info(message)


def UI_BusyStop():
    debug_logger.debug('UI_BusyStop: %s', UI_mode)


def diff(oldprofile, newprofile):
    difftemp = NamedTemporaryFile('w')
    subprocess.call('diff -u -p %s %s > %s' % (oldprofile, newprofile, difftemp.name), shell=True)
    return difftemp


def write_profile_to_tempfile(profile):
    temp = NamedTemporaryFile('w')
    temp.write(profile)
    temp.flush()
    return temp


def generate_diff(oldprofile, newprofile):
    with write_profile_to_tempfile(oldprofile) as oldtemp, \
            write_profile_to_tempfile(newprofile) as newtemp:
        return diff(oldtemp.name, newtemp.name)


def generate_diff_with_comments(oldprofile, newprofile):
    if not os.path.exists(oldprofile):
        raise AppArmorException(_("Can't find existing profile %s to compare changes.") % oldprofile)
    with write_profile_to_tempfile(newprofile) as newtemp:
        return diff(oldprofile, newtemp.name)


def UI_Changes(oldprofile, newprofile, comments=False):
    if not comments:
        difftemp = generate_diff(oldprofile, newprofile)
        header = 'View Changes'
    else:
        difftemp = generate_diff_with_comments(oldprofile, newprofile)
        header = 'View Changes with comments'
    with difftemp:
        UI_ShowFile(header, difftemp.name)


def UI_ShowFile(header, filename):
    if UI_mode == 'json':
        jsonout = {'dialog': 'changes', 'header': header, 'filename': filename}
        write_json(jsonout)
        json_response('changes')["response"]  # wait for response to delay deletion of filename (and ignore response content)
    else:
        subprocess.call(['less', filename])


CMDS = {'CMD_ALLOW': _('(A)llow'),
        'CMD_OTHER': _('(M)ore'),
        'CMD_AUDIT_NEW': _('Audi(t)'),
        'CMD_AUDIT_OFF': _('Audi(t) off'),
        'CMD_AUDIT_FULL': _('Audit (A)ll'),
        # 'CMD_OTHER': '(O)pts',
        'CMD_USER_ON': _('(O)wner permissions on'),
        'CMD_USER_OFF': _('(O)wner permissions off'),
        'CMD_DENY': _('(D)eny'),
        'CMD_ABORT': _('Abo(r)t'),
        'CMD_FINISHED': _('(F)inish'),
        'CMD_ix': _('In(h)erit'),
        'CMD_px': _('(P)rofile'),
        'CMD_px_safe': _('(P)rofile Clean Exec'),
        'CMD_cx': _('(C)hild'),
        'CMD_cx_safe': _('(C)hild Clean Exec'),
        'CMD_nx': _('(N)amed'),
        'CMD_nx_safe': _('(N)amed Clean Exec'),
        'CMD_ux': _('(U)nconfined'),
        'CMD_ux_safe': _('(U)nconfined Clean Exec'),
        'CMD_pix': _('(P)rofile Inherit'),
        'CMD_pix_safe': _('(P)rofile Inherit Clean Exec'),
        'CMD_cix': _('(C)hild Inherit'),
        'CMD_cix_safe': _('(C)hild Inherit Clean Exec'),
        'CMD_nix': _('(N)amed Inherit'),
        'CMD_nix_safe': _('(N)amed Inherit Clean Exec'),
        'CMD_EXEC_IX_ON': _('(X) ix On'),
        'CMD_EXEC_IX_OFF': _('(X) ix Off'),
        'CMD_SAVE': _('(S)ave Changes'),
        'CMD_NEW': _('(N)ew'),
        'CMD_GLOB': _('(G)lob'),
        'CMD_GLOBEXT': _('Glob with (E)xtension'),
        'CMD_ADDHAT': _('(A)dd Requested Hat'),
        'CMD_ADDSUBPROFILE': _('(A)dd Requested Subprofile'),
        'CMD_USEDEFAULT': _('(U)se Default Hat'),
        'CMD_SCAN': _('(S)can system log for AppArmor events'),
        'CMD_HELP': _('(H)elp'),
        'CMD_VIEW_PROFILE': _('(V)iew Profile'),
        'CMD_USE_PROFILE': _('(U)se Profile'),
        'CMD_CREATE_PROFILE': _('(C)reate New Profile'),
        'CMD_UPDATE_PROFILE': _('(U)pdate Profile'),
        'CMD_IGNORE_UPDATE': _('(I)gnore Update'),
        'CMD_SAVE_CHANGES': _('(S)ave Changes'),
        'CMD_SAVE_SELECTED': _('Save Selec(t)ed Profile'),
        'CMD_VIEW_CHANGES': _('(V)iew Changes'),
        'CMD_VIEW_CHANGES_CLEAN': _('View Changes b/w (C)lean profiles'),
        'CMD_VIEW': _('(V)iew'),
        'CMD_ENABLE_REPO': _('(E)nable Repository'),
        'CMD_DISABLE_REPO': _('(D)isable Repository'),
        'CMD_YES': _('(Y)es'),
        'CMD_NO': _('(N)o'),
        'CMD_CANCEL': _('(C)ancel'),
        'CMD_ALL_NET': _('Allow All (N)etwork'),
        'CMD_NET_FAMILY': _('Allow Network Fa(m)ily'),
        'CMD_OVERWRITE': _('(O)verwrite Profile'),
        'CMD_KEEP': _('(K)eep Profile'),
        'CMD_IGNORE_ENTRY': _('(I)gnore')
        }


class PromptQuestion:
    title = None
    headers = None
    explanation = None
    functions = None
    options = None
    default = None
    selected = None
    helptext = None
    already_have_profile = False

    def __init__(self):
        self.headers = []
        self.functions = []
        self.selected = 0

    def promptUser(self, params=''):
        cmd = None
        arg = None
        cmd, arg = self.Text_PromptUser()
        if cmd == 'CMD_ABORT':
            confirm_and_abort()
            cmd = 'XXXINVALIDXXX'
        return (cmd, arg)

    def Text_PromptUser(self):
        title = self.title
        explanation = self.explanation
        headers = self.headers
        functions = self.functions

        default = self.default
        options = self.options
        selected = self.selected
        helptext = self.helptext

        if helptext:
            functions.append('CMD_HELP')

        menu_items = []
        keys = dict()

        for cmd in functions:
            if not CMDS.get(cmd, False):
                raise AppArmorException(_('PromptUser: Unknown command %s') % cmd)

            menutext = CMDS[cmd]

            key = get_translated_hotkey(menutext)
            # Duplicate hotkey
            if keys.get(key, False):
                raise AppArmorException(
                    _('PromptUser: Duplicate hotkey for %(command)s: %(menutext)s ')
                    % {'command': cmd, 'menutext': menutext})

            keys[key] = cmd

            if default and default == cmd:
                menutext = '[%s]' % menutext

            menu_items.append(menutext)

        default_key = 0
        if default and CMDS[default]:
            defaulttext = CMDS[default]
            defmsg = _('PromptUser: Invalid hotkey in default item')

            default_key = get_translated_hotkey(defaulttext, defmsg)

            if not keys.get(default_key, False):
                raise AppArmorException(_('PromptUser: Invalid default %s') % default)

        widest = 0
        header_copy = headers[:]
        while header_copy:
            header = header_copy.pop(0)
            header_copy.pop(0)
            if len(header) > widest:
                widest = len(header)
        widest += 1

        formatstr = '%-' + str(widest) + 's %s\n'

        function_regexp = '^('
        function_regexp += '|'.join(keys.keys())
        if options:
            function_regexp += r'|\d'
        function_regexp += ')$'

        ans = 'XXXINVALIDXXX'
        hdict = dict()
        jsonprompt = {
            'dialog': 'promptuser',
            'title': title,
            'headers': hdict,
            'explanation': explanation,
            'options': options,
            'menu_items': menu_items,
            'default_key': default_key,
        }

        while not re.search(function_regexp, ans, flags=re.IGNORECASE):

            prompt = '\n'
            if title:
                prompt += '= %s =\n\n' % title

            if headers:
                header_copy = headers[:]
                while header_copy:
                    header = header_copy.pop(0)
                    value = header_copy.pop(0)
                    hdict[header] = value
                    prompt += formatstr % (header + ':', value)
                prompt += '\n'

            if explanation:
                prompt += explanation + '\n\n'

            if options:
                for index, option in enumerate(options):
                    if selected == index:
                        format_option = ' [%s - %s]'
                    else:
                        format_option = '  %s - %s '
                    prompt += format_option % (index + 1, option)
                    prompt += '\n'

            prompt += ' / '.join(menu_items)

            if UI_mode == 'json':
                write_json(jsonprompt)
                hm = json_response('promptuser')
                ans = hm["response_key"]
                selected = hm["selected"]

            elif UI_mode == 'allow_all':
                if self.already_have_profile:
                    expected_keys = ['CMD_px', 'CMD_ix', 'CMD_ALLOW', 'CMD_SAVE_CHANGES']
                else:
                    expected_keys = ['CMD_ix', 'CMD_ALLOW', 'CMD_SAVE_CHANGES']
                for exp in expected_keys:
                    if exp in functions:
                        ans = get_translated_hotkey(CMDS[exp])
                        break

            else:  # text mode
                sys.stdout.write(prompt + '\n')
                ans = getkey().lower()

            if ans:
                if ans == 'up':
                    if options and selected > 0:
                        selected -= 1
                    ans = 'XXXINVALIDXXX'

                elif ans == 'down':
                    if options and selected < len(options) - 1:
                        selected += 1
                    ans = 'XXXINVALIDXXX'

    #             elif keys.get(ans, False) == 'CMD_HELP':
    #                 sys.stdout.write('\n%s\n' %helptext)
    #                 ans = 'XXXINVALIDXXX'

                elif is_number(ans) == 10:
                    # If they hit return choose default option
                    ans = default_key

                elif options and re.search(r'^\d$', ans):
                    ans = int(ans)
                    if ans > 0 and ans <= len(options):
                        selected = ans - 1
                    ans = 'XXXINVALIDXXX'

            if keys.get(ans, False) == 'CMD_HELP' and UI_mode != 'json':
                sys.stdout.write('\n%s\n' % helptext)
                ans = 'again'

        if keys.get(ans, False):
            ans = keys[ans]

        return ans, selected


def confirm_and_abort():
    ans = UI_YesNo(_('Are you sure you want to abandon this set of profile changes and exit?'), 'n')
    if ans == 'y':
        UI_Info(_('Abandoning all changes.'))
        sys.exit(0)


def is_number(number):
    try:
        return int(number)
    except (TypeError, ValueError):
        return False
