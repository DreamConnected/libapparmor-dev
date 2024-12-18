# ----------------------------------------------------------------------
#    Copyright (C) 2013 Kshitij Gupta <kgupta8592@gmail.com>
#    Copyright (C) 2015-2024 Christian Boltz <apparmor@cboltz.de>
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
import os
import sys
from shutil import which

import apparmor.aa as apparmor
import apparmor.ui as aaui
from apparmor.common import AppArmorException, cmd, is_skippable_file, user_perm
from apparmor.translations import init_translation

_ = init_translation()


class aa_tools:
    def __init__(self, tool_name, args):
        apparmor.init_aa(profiledir=args.dir, confdir=args.configdir)
        apparmor.read_profiles()

        if not user_perm(apparmor.profile_dir):
            raise AppArmorException("Cannot write to profile directory: %s" % (apparmor.profile_dir))

        self.name = tool_name
        self.profiling = args.program
        self.silent = None
        self.do_reload = args.do_reload

        if tool_name == 'audit':
            self.remove = args.remove
        elif tool_name == 'autodep':
            self.force = args.force
            self.aa_mountpoint = apparmor.check_for_apparmor()
        elif tool_name == 'cleanprof':
            self.silent = args.silent

    def get_next_to_profile(self):
        """Iterator function to walk the list of arguments passed"""

        for p in self.profiling:
            if not p:
                continue

            if os.path.exists(p) or p.startswith('/'):
                fq_path = apparmor.get_full_path(p).strip()
                if os.path.commonprefix([apparmor.profile_dir, fq_path]) == apparmor.profile_dir:
                    program = None
                    prof_filename = fq_path
                    profile = None
                else:
                    program = fq_path
                    profile = apparmor.active_profiles.profile_from_attachment(fq_path)
                    prof_filename = apparmor.get_profile_filename_from_attachment(fq_path, True)
            else:
                which_ = which(p)
                if self.name == 'cleanprof' and apparmor.active_profiles.profile_exists(p):
                    program = p  # not really correct, but works
                    profile = p
                    prof_filename = apparmor.get_profile_filename_from_profile_name(profile)
                elif which_ is not None:
                    program = apparmor.get_full_path(which_)
                    profile = program
                    prof_filename = apparmor.get_profile_filename_from_attachment(program, True)
                elif os.path.exists(os.path.join(apparmor.profile_dir, p)):
                    program = None
                    profile = p
                    prof_filename = apparmor.get_full_path(os.path.join(apparmor.profile_dir, p)).strip()
                else:
                    if '/' not in p:
                        aaui.UI_Info(_("Can't find %(program)s in the system path list. If the name of the application\nis correct, please run 'which %(program)s' as a user with correct PATH\nenvironment set up in order to find the fully-qualified path and\nuse the full path as parameter.")
                                     % {'program': p})
                    else:
                        aaui.UI_Info(_("%s does not exist, please double-check the path.") % p)

                    continue

            yield (program, profile, prof_filename)

    def get_next_for_modechange(self):
        """common code for mode/flags changes"""

        for (program, _ignored, prof_filename) in self.get_next_to_profile():
            output_name = prof_filename if program is None else program

            if not os.path.isfile(prof_filename) or is_skippable_file(prof_filename):
                aaui.UI_Info(_('Profile for %s not found, skipping') % output_name)
                continue

            yield (program, prof_filename, output_name)

    def cleanprof_act(self):
        for (program, profile, prof_filename) in self.get_next_to_profile():
            if program is None:
                program = profile

            if not program or not (os.path.exists(program) or apparmor.active_profiles.profile_exists(profile)):
                if program and not program.startswith('/'):
                    program = aaui.UI_GetString(_('The given program cannot be found, please try with the fully qualified path name of the program: '), '')
                else:
                    aaui.UI_Info(_("%s does not exist, please double-check the path.") % program)
                    sys.exit(1)

            if program and apparmor.active_profiles.profile_exists(profile):
                self.clean_profile(program, profile, prof_filename)

            else:
                if '/' not in program:
                    aaui.UI_Info(_("Can't find %(program)s in the system path list. If the name of the application\nis correct, please run 'which %(program)s' as a user with correct PATH\nenvironment set up in order to find the fully-qualified path and\nuse the full path as parameter.")
                                 % {'program': program})
                else:
                    aaui.UI_Info(_("%s does not exist, please double-check the path.") % program)
                    sys.exit(1)

    def cmd_disable(self):
        for (program, prof_filename, output_name) in self.get_next_for_modechange():
            aaui.UI_Info(_('Disabling %s.') % output_name)

            apparmor.create_symlink('disable', prof_filename)

            self.unload_profile(prof_filename)

    def cmd_enforce(self):
        for (program, prof_filename, output_name) in self.get_next_for_modechange():
            apparmor.set_enforce(prof_filename, program)

            self.reload_profile(prof_filename)

    def cmd_complain(self):
        for (program, prof_filename, output_name) in self.get_next_for_modechange():
            apparmor.set_complain(prof_filename, program)

            self.reload_profile(prof_filename)

    def cmd_audit(self):
        for (program, prof_filename, output_name) in self.get_next_for_modechange():

            # keep this to allow toggling 'audit' flags
            if not self.remove:
                aaui.UI_Info(_('Setting %s to audit mode.') % output_name)
            else:
                aaui.UI_Info(_('Removing audit mode from %s.') % output_name)
            apparmor.change_profile_flags(prof_filename, program, 'audit', not self.remove)

            disable_link = '%s/disable/%s' % (apparmor.profile_dir, os.path.basename(prof_filename))

            if os.path.exists(disable_link):
                aaui.UI_Info(_('\nWarning: the profile %s is disabled. Use aa-enforce or aa-complain to enable it.') % os.path.basename(prof_filename))

            self.reload_profile(prof_filename)

    def cmd_autodep(self):
        apparmor.loadincludes()

        for (program, _ignored, prof_filename) in self.get_next_to_profile():
            if not program:
                aaui.UI_Info(_('Please pass an application to generate a profile for, not a profile itself - skipping %s.') % prof_filename)
                continue

            apparmor.check_qualifiers(program)

            if os.path.exists(apparmor.get_profile_filename_from_attachment(program, True)) and not self.force:
                aaui.UI_Info(_('Profile for %s already exists - skipping.') % program)
            else:
                apparmor.autodep(program)
                if self.aa_mountpoint:
                    apparmor.reload(program)

    def clean_profile(self, program, profile, prof_filename):
        import apparmor.cleanprofile as cleanprofile

        prof = cleanprofile.Prof(prof_filename)
        cleanprof = cleanprofile.CleanProf(True, prof, prof)
        deleted = cleanprof.remove_duplicate_rules(profile)
        aaui.UI_Info(_("\nDeleted %s rules.") % deleted)
        apparmor.changed[profile] = True

        if not prof_filename:
            raise AppArmorException(_('The profile for %s does not exists. Nothing to clean.') % program)

        if self.silent:
            apparmor.write_profile_ui_feedback(profile, True)
            self.reload_profile(prof_filename)
        else:
            q = aaui.PromptQuestion()
            q.title = 'Changed Local Profiles'
            q.explanation = _('The local profile for %(program)s in file %(file)s was changed. Would you like to save it?') % {'program': program, 'file': prof_filename}
            q.functions = ['CMD_SAVE_CHANGES', 'CMD_VIEW_CHANGES', 'CMD_ABORT']
            q.default = 'CMD_VIEW_CHANGES'
            q.options = []
            q.selected = 0
            ans = ''
            arg = None
            while ans != 'CMD_SAVE_CHANGES':
                ans, arg = q.promptUser()
                if ans == 'CMD_SAVE_CHANGES':
                    apparmor.write_profile_ui_feedback(profile)
                    self.reload_profile(prof_filename)
                elif ans == 'CMD_VIEW_CHANGES':
                    # oldprofile = apparmor.serialize_profile(apparmor.original_profiles, profile, {})
                    newprofile = apparmor.serialize_profile(apparmor.active_profiles, profile, {})  # , {'is_attachment': True})
                    aaui.UI_Changes(prof_filename, newprofile, comments=True)

    def unload_profile(self, prof_filename):
        if not self.do_reload:
            return

        # FIXME: should ensure profile is loaded before unloading
        cmd_info = cmd([apparmor.parser, '-I%s' % apparmor.profile_dir, '--base', apparmor.profile_dir, '-R', prof_filename])

        if cmd_info[0] != 0:
            raise AppArmorException(cmd_info[1])

    def reload_profile(self, prof_filename):
        if not self.do_reload:
            return

        apparmor.reload_profile(prof_filename, raise_exc=True)
