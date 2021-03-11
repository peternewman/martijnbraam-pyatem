import json
import threading
import time

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

has_midi = False
try:
    import rtmidi
    from rtmidi.midiutil import open_midiinput, open_midioutput, list_available_ports

    has_midi = True
except ImportError as e:
    print("Module 'rtmidi' not found, skipping midi support")


class MidiConnection(threading.Thread):
    def __init__(self, port, callback):
        threading.Thread.__init__(self)
        self.callback = callback
        self.port = port
        self.output = None
        self.enabled = False

    def run(self):
        if not has_midi:
            return

        def _midi_in(event, data=None):
            self._do_callback(*event[0])

        if self.port is None:
            temp = rtmidi.MidiIn()
            ports = temp.get_ports()
            for port in ports:
                if 'Midi Through' in port:
                    continue
                break
            else:
                print("No suitable midi port found")
                return
            self.port = port

        midiin, port_name = open_midiinput(self.port, client_name="Switcher")
        midiout, port_name = open_midioutput(self.port, client_name="Switcher")
        self.output = midiout
        midiin.set_callback(_midi_in)
        self.enabled = True

        while True:
            time.sleep(10)

    def _do_callback(self, *args, **kwargs):
        GLib.idle_add(self.callback, *args, **kwargs)

    def send(self, *args):
        if self.enabled:
            self.output.send_message(args)


class MidiLink:
    def __init__(self, widget, key, midi):
        if hasattr(widget, 'dynamic_id'):
            self.name = 'dyn:' + widget.dynamic_id
        else:
            try:
                self.name = Gtk.Buildable.get_name(widget)
            except:
                return
        self.type = None
        self.key = key
        self.midi = midi
        self.widget = widget
        self.adjustment = None
        self.min = None
        self.max = None
        self.is_tbar = False
        self.inverted = False

        if isinstance(widget, gi.repository.Gtk.Scale):
            self.type = 'scale'
            self.adjustment = widget.get_adjustment()
            self.min = self.adjustment.get_lower()
            self.max = self.adjustment.get_upper()
            if hasattr(widget, 'is_tbar') and widget.is_tbar:
                self.is_tbar = True
                self.widget.connect("notify::inverted", self.on_tbar_inverted)
        if isinstance(widget, gi.repository.Gtk.Button):
            self.type = 'button'
            self.widget.connect("style-updated", self.on_style_changed)

        print("New midi mapping: {} <-> {}".format(key, self.name))

    def new_value(self, value):
        if self.type == 'button':
            self.widget.emit("clicked")
        if self.type == 'scale':
            self.widget.tbar_held = True
            if self.inverted:
                self.adjustment.set_value(self._remap(127, 0, self.min, self.max, value))
            else:
                self.adjustment.set_value(self._remap(0, 127, self.min, self.max, value))
            self.widget.tbar_held = False

    def _remap(self, in_min, in_max, out_min, out_max, value):
        in_range = in_max - in_min
        out_range = out_max - out_min
        return (((value - in_min) * out_range) / in_range) + out_min

    def on_tbar_inverted(self, *args):
        self.inverted = not self.inverted

    def on_style_changed(self, *args):
        value = 0
        if self.widget.get_style_context().has_class('active'):
            value = 127
        if self.widget.get_style_context().has_class('program'):
            value = 127
        if self.widget.get_style_context().has_class('preview'):
            value = 127
        self.midi.send(*self.key, value)


class MidiControl:
    def __init__(self, builder):
        self.midi = MidiConnection(None, self.on_midi)
        self.midi.daemon = True
        self.midi.start()

        self.midi_map = {}

        self.menu = None
        self.midi_learning = False
        self.midi_learning_widget = None

        mapstr = self.settings.get_string('midi-map')
        map = json.loads(mapstr)
        self.restore_midi_map(map, builder)

    def on_midi(self, event, channel, value):
        if event == 176 or event == 144:
            # CC and NoteOn
            key = (event, channel)
            print(event, channel, value)

            if key in self.midi_map:
                self.midi_map[key].new_value(value)

            if self.midi_learning:
                self.midi_learning = False
                self.midi_map[key] = MidiLink(self.midi_learning_widget, key, self.midi)
                self.midi_learning_widget = None
                self.save_midi_map()

    def on_context_menu(self, widget, event, *args):
        if event.button != 3:
            return

        self.menu = Gtk.Menu()
        midi_item = Gtk.MenuItem("Midi learn")
        midi_item.connect('activate', self.on_start_midi_learn)
        self.menu.append(midi_item)
        self.menu.show_all()
        self.menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())
        self.midi_learning_widget = widget

    def on_start_midi_learn(self, *args):
        self.midi_learning = True

    def restore_midi_map(self, map, builder):
        for line in map:
            *key, widget_name = line
            key = tuple(*key)
            if 'dyn:' in widget_name:
                pass
            else:
                widget = builder.get_object(widget_name)
            link = MidiLink(widget, key, self.midi)
            self.midi_map[key] = link

    def save_midi_map(self):
        result = []
        for key in self.midi_map:
            result.append([key, self.midi_map[key].name])

        js = json.dumps(result)
        self.settings.set_string('midi-map', js)