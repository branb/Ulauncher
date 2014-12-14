# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import logging
import datetime
import threading
from gi.repository import Gtk, Gdk, Keybinder

from ulauncher_lib import Window
from ulauncher.AboutUlauncherDialog import AboutUlauncherDialog
from ulauncher.PreferencesUlauncherDialog import PreferencesUlauncherDialog
from . results import find_results_for_input
from . results.Navigation import Navigation
from . backend.apps import start_sync

logger = logging.getLogger(__name__)


class UlauncherWindow(Window):
    __gtype_name__ = "UlauncherWindow"

    def get_widget(self, id):
        """
        Return widget instance by its ID
        """
        return self.builder.get_object(id)

    def finish_initializing(self, builder):
        """
        Set up the main window
        """
        super(UlauncherWindow, self).finish_initializing(builder)

        self.results_nav = None
        self.builder = builder
        self.window = self.get_widget('ulauncher_window')
        self.input = self.get_widget('input')
        self.result_box = builder.get_object("result_box")

        self.input.connect('changed', self.on_input_changed)

        self.set_keep_above(True)

        self.AboutDialog = AboutUlauncherDialog
        self.PreferencesDialog = PreferencesUlauncherDialog

        self.position_window()
        self.init_styles()
        self.bind_keys()
        start_sync()

    def position_window(self):
        window_width = self.get_size()[0]
        self.move(Gdk.Screen.width() / 2 - window_width / 2, Gdk.Screen.height() / 3)

    def init_styles(self):
        self.provider = Gtk.CssProvider()
        self.provider.load_from_path('data/ui/ulauncher.css')
        self.apply_css(self, self.provider)
        self.screen = self.get_screen()
        self.visual = self.screen.get_rgba_visual()
        if self.visual is not None and self.screen.is_composited():
            self.set_visual(self.visual)

    def apply_css(self, widget, provider):
        Gtk.StyleContext.add_provider(widget.get_style_context(),
                                      provider,
                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        if isinstance(widget, Gtk.Container):
            widget.forall(self.apply_css, provider)

    def on_focus_out_event(self, *args):
        # apparently Gtk doesn't provide a mechanism to tell if window is in focus
        # this is a simple workaround to avoid hiding window
        # when user hits Alt+key combination or changes input source, etc.
        self.is_focused = False
        t = threading.Timer(0.07, lambda: self.is_focused or self.hide())
        t.start()

    def on_focus_in_event(self, *args):
        self.is_focused = True

    def show_window(self):
        # works only when the following methods are called in that exact order
        self.input.set_text('')
        self.position_window()
        self.window.set_sensitive(True)
        self.window.present()
        self.present_with_time(Keybinder.get_current_event_time())

    def cb_toggle_visibility(self, key):
        self.hide() if self.is_visible() else self.show_window()

    def bind_keys(self):
        logger.info("Trying to bind hotkeys")
        Keybinder.init()
        Keybinder.bind("<Ctrl>space", self.cb_toggle_visibility)

    def on_input_changed(self, entry):
        """
        Triggered by user input
        """
        query = entry.get_text()
        if query:
            find_results_for_input(query, self.on_results)
        else:
            self.on_results([])

    def on_results(self, results):
        self.results_nav = None
        self.result_box.foreach(lambda w: w.destroy())
        results = list(results)
        if results:
            map(self.result_box.add, results)
            self.result_box.show_all()
            self.result_box.set_margin_bottom(10)
            self.results_nav = Navigation(self.result_box.get_children())
            self.results_nav.select(0)
            self.apply_css(self.result_box, self.provider)
        else:
            self.result_box.set_margin_bottom(0)

    KEY_UP = 111
    KEY_DOWN = 116
    KEY_ENTER = 36
    KEY_ESC = 9

    def on_key_press_event(self, widget, event):
        keycode = event.get_keycode()[1]

        if self.results_nav:
            if keycode == self.KEY_UP:
                self.results_nav.go_up()
            elif keycode == self.KEY_DOWN:
                self.results_nav.go_down()
            elif keycode == self.KEY_ENTER:
                if self.results_nav.enter():
                    self.hide()

        if keycode == self.KEY_ESC:
            self.hide()