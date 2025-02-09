import os
import tkinter as tk
import tkinter.font as Font
import tkinter.ttk as ttk
import subprocess

try:  # We use tk without themes as a fallback which makes the GUI uglier but functional.
    import ttkthemes
except ImportError:
    print(_("tksthemes not found. Install for best user experience."))
    ttkthemes = None


import apparmor.aa as aa

from apparmor.translations import init_translation

_ = init_translation()

notification_custom_msg = {
    'userns': _('Application {0} wants to create an user namespace which could be used to compromise your system\nDo you want to allow it next time {0} is run?')
}

global interface_theme


class GUI:
    def __init__(self):
        try:
            self.master = tk.Tk()
        except tk.TclError:
            print(_('ERROR: Cannot initialize Tkinter. Please check that your terminal can use a graphical interface'))
            os._exit(1)

        self.result = None
        if ttkthemes:
            style = ttkthemes.ThemedStyle(self.master)
            style.theme_use(interface_theme)
            self.bg_color = style.lookup('TLabel', 'background')
            self.fg_color = style.lookup('TLabel', 'foreground')
            self.master.configure(background=self.bg_color)
        self.label_frame = ttk.Frame(self.master, padding=(20, 10))
        self.label_frame.pack(fill='both', expand=True)

        self.button_frame = ttk.Frame(self.master, padding=(10, 10))
        self.button_frame.pack(fill='x', expand=True)

    def show(self):
        self.master.mainloop()
        return self.result

    def set_result(self, result):
        self.result = result
        self.master.destroy()


class ShowMoreGUI(GUI):
    def __init__(self, profile_path, msg, rule, profile_name, profile_found=True):
        self.rule = rule
        self.profile_name = profile_name
        self.profile_path = profile_path
        self.msg = msg
        self.profile_found = profile_found

        super().__init__()

        self.master.title(_('AppArmor - More info'))

        self.label = tk.Label(self.label_frame, text=self.msg, anchor='w', justify=tk.LEFT, wraplength=460)
        if ttkthemes:
            self.label.configure(background=self.bg_color, foreground=self.fg_color)
        self.label.pack(pady=(0, 10) if not self.profile_found else (0, 0))

        if self.profile_found:
            self.show_profile_button = ttk.Button(self.button_frame, text=_('Show Current Profile'), command=lambda: open_with_default_editor(self.profile_path))
            self.show_profile_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            self.add_to_profile_button = ttk.Button(self.button_frame, text=_('Allow'), command=lambda: self.set_result('add_rule'))
            self.add_to_profile_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        elif rule == 'userns create,':
            self.add_policy_button = ttk.Button(self.master, text=_('Allow'), command=lambda: self.set_result('allow'))
            self.add_policy_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            self.never_ask_button = ttk.Button(self.master, text=_('Deny'), command=lambda: self.set_result('deny'))
            self.never_ask_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            self.do_nothing_button = ttk.Button(self.master, text=_('Do nothing'), command=self.master.destroy)
            self.do_nothing_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)


class ProfileRules:
    def __init__(self, raw_rules, selectable, profile_name, profile_path, is_userns_profile, bin_name, bin_path):
        self.selectable = selectable
        self.rules = []
        self.profile_name = profile_name
        self.profile_path = profile_path
        self.is_userns_profile = is_userns_profile
        self.bin_name = bin_name
        self.bin_path = bin_path

        for raw_rule in raw_rules:
            self.rules.append(SelectableRule(raw_rule, self.selectable))

    def get_writable_rules(self, template_path, allow_all=False):
        out = ''
        for rule in self.rules:
            if allow_all or rule.selected.get():
                if not self.is_userns_profile:
                    out += 'add_rule\t{}\t{}\n'.format(rule.rule, self.profile_name)
                else:
                    out += 'create_userns\t{}\t{}\t{}\t{}\t{}\n'.format(template_path, self.profile_name, self.bin_path, self.profile_path, 'allow')
        return out


class SelectableRule:
    def __init__(self, rule, selectable):
        self.rule = rule
        self.selectable = selectable
        self.selected = None

    def create_checkbox_rule(self, rules_frame):
        self.selected = tk.IntVar(value=self.selectable)
        return ttk.Checkbutton(rules_frame, text=self.rule, variable=self.selected, state=tk.DISABLED if not self.selectable else tk.ACTIVE)

    def toggle(self):
        self.selected.set(0 if self.selected else 1)


class ShowMoreGUIAggregated(GUI):
    def __init__(self, summary, detailed_text, clean_rules):
        self.summary = summary
        self.detailed_text = detailed_text
        self.clean_rules = clean_rules

        self.states = {
            'summary': {
                'msg': self.summary,
                'btn_left': _('Show more details'),
                'btn_right': _('Show rules only')
            },
            'detailed': {
                'msg': self.detailed_text,
                'btn_left': _('Show summary'),
                'btn_right': _('Show rules only')
            },
            'rules_only': {
                'btn_left': _('Show more details'),
                'btn_right': _('Show summary')
            }
        }

        self.state = 'rules_only'

        super().__init__()

        self.master.title(_('AppArmor - More info'))
        self.scrollbar = ttk.Scrollbar(self.label_frame)
        self.scrollbar.pack(side='right', fill='y')

        self.text_display = tk.Text(self.label_frame, wrap='word', height=40, width=100, yscrollcommand=self.scrollbar.set)

        if ttkthemes:
            self.text_display.configure(background=self.bg_color, foreground=self.fg_color)
        self.canvas = tk.Canvas(
            self.label_frame,
            background=self.bg_color,
            height=self.text_display.winfo_reqheight() - 4,  # The border are *inside* the canvas but *outside* the textbox. I need to remove 4px (2*the size of the borders) to get the same size
            width=self.text_display.winfo_reqwidth() - 4,
            borderwidth=self.text_display['borderwidth'],
            relief=self.text_display['relief'],
            yscrollcommand=self.scrollbar.set
        )

        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((2, 2), window=self.inner_frame, anchor='nw')

        self.create_profile_rules_frame(self.inner_frame, self.clean_rules)
        self.init_widgets()

        self.btn_left = ttk.Button(self.button_frame, text=self.states[self.state]['btn_left'], width=1, command=lambda: self.change_view('btn_left'))
        self.btn_left.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.btn_right = ttk.Button(self.button_frame, text=self.states[self.state]['btn_right'], width=1, command=lambda: self.change_view('btn_right'))
        self.btn_right.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.btn_allow_selected = ttk.Button(self.button_frame, text="Allow Selected", width=1, command=lambda: self.set_result('allow_selected'))
        self.btn_allow_selected.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        for i in range(3):
            self.button_frame.grid_columnconfigure(i, weight=1)

    def init_widgets(self):
        self.text_display.pack_forget()
        self.canvas.pack_forget()

        if self.state == 'rules_only':
            self.scrollbar.config(command=self.canvas.yview)
            self.canvas.pack(side='left', fill='both', expand=True)

        else:
            self.scrollbar.config(command=self.text_display.yview)
            self.text_display['state'] = 'normal'
            self.text_display.delete('1.0', 'end')
            self.text_display.insert('1.0', self.states[self.state]['msg'])
            self.text_display['state'] = 'disabled'
            self.text_display.pack(side='left', fill='both', expand=True)

    def create_profile_rules_frame(self, parent, clean_rules):
        for profile_name, profile_rules in clean_rules.items():
            label = ttk.Label(parent, text=profile_name, font=tk.font.BOLD)
            label.pack(anchor='w', pady=(5, 0))
            label.bind("<Button-1>", lambda event, rules=profile_rules: self.toggle_profile_rules(rules))

            rules_frame = ttk.Frame(parent)
            rules_frame.pack(fill='x', padx=20)

            for rule in profile_rules.rules:
                rule.create_checkbox_rule(rules_frame).pack(anchor='w')

    @staticmethod
    def toggle_profile_rules(profile_rules):
        action = 0 if all(var.selected.get() for var in profile_rules.rules) else 1
        for var in profile_rules.rules:
            if var.selectable:
                var.selected.set(action)

    def change_view(self, action):
        if action == 'btn_left':
            self.state = 'detailed' if self.state != 'detailed' else 'summary'
        elif action == 'btn_right':
            self.state = 'rules_only' if self.state != 'rules_only' else 'summary'

        self.btn_left['text'] = self.states[self.state]['btn_left']
        self.btn_right['text'] = self.states[self.state]['btn_right']

        self.init_widgets()

        if self.state != 'rules_only':
            self.text_display['state'] = 'normal'
            self.text_display.delete('1.0', 'end')
            self.text_display.insert('1.0', self.states[self.state]['msg'])
            self.text_display['state'] = 'disabled'


class UsernsGUI(GUI):
    def __init__(self, name, path):
        self.name = name
        self.path = path

        super().__init__()

        self.master.title(_('AppArmor - User namespace creation restricted'))

        label_text = notification_custom_msg['userns'].format(name)
        self.label = ttk.Label(self.label_frame, text=label_text, wraplength=460)
        self.label.pack()
        link = ttk.Label(self.master, text=_('More information'), foreground='blue', cursor='hand2')
        link.pack()
        link.bind('<Button-1>', self.more_info)

        self.add_policy_button = ttk.Button(self.master, text=_('Allow'), command=lambda: self.set_result('allow'))
        self.add_policy_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.never_ask_button = ttk.Button(self.master, text=_('Deny'), command=lambda: self.set_result('deny'))
        self.never_ask_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.do_nothing_button = ttk.Button(self.master, text=_('Do nothing'), command=self.master.destroy)
        self.do_nothing_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def more_info(self, ev):
        more_info_text = _("""
In Linux, user namespaces enable non-root users to perform certain privileged operations. This feature can be useful for several legitimate use cases.

However, this feature also introduces security risks, (e.g. privilege escalation exploits).

This dialog allows you to choose whether you want to enable user namespaces for this application.

The application path is {}""".format(self.path))
        # Rule=None so we don't show redundant buttons in ShowMoreGUI.
        more_gui = ShowMoreGUI(self.path, more_info_text, None, self.name, profile_found=False)
        more_gui.show()

    @staticmethod
    def show_error_cannot_reload_profile(profile_path, error):
        ErrorGUI(_('Failed to create or load profile {}\n Error code = {}').format(profile_path, error), False).show()

    @staticmethod
    def show_error_cannot_find_execpath(name, template_path):
        ErrorGUI(
            _(
                'Application {0} wants to create an user namespace which could be used to compromise your system\n\n'
                'However, apparmor cannot find {0}. If you want to allow it, please create a profile for it.\n\n'
                'A profile template is in {1}\n Profiles are in {2}'
            ).format(name, template_path, aa.profile_dir),
            False
        ).show()


class ErrorGUI(GUI):
    def __init__(self, msg, is_fatal):
        self.msg = msg
        self.is_fatal = is_fatal

        super().__init__()

        self.master.title('AppArmor Error')

        self.label = ttk.Label(self.label_frame, text=self.msg, wraplength=460)
        if ttkthemes:
            self.label.configure(background=self.bg_color)
        self.label.pack()

        self.button = ttk.Button(self.button_frame, text='OK', command=self.destroy)
        self.button.pack()

    def destroy(self):
        self.master.destroy()

        if self.is_fatal:
            os._exit(1)

    def show(self):
        self.master.mainloop()
        if self.is_fatal:
            os._exit(1)


def set_interface_theme(theme):
    global interface_theme
    interface_theme = theme


def open_with_default_editor(profile_path):
    try:
        default_app = subprocess.run(['xdg-mime', 'query', 'default', 'text/plain'], capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(['gtk-launch', default_app, profile_path], check=True)
    except subprocess.CalledProcessError:
        ErrorGUI(_('Failed to launch default editor'), False).show()
    except FileNotFoundError as e:
        ErrorGUI(_('Failed to open file: {}').format(e), False).show()
