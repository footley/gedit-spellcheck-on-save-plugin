"""
A gedit plugin which performs a spellcheck on *.md,*.txt files whenever one is 
saved.
"""

import re
import os
import sys
import enchant
from gi.repository import GObject, Gtk, Gedit, Gio # pylint: disable=E0611
from gi.repository import Pango, PeasGtk # pylint: disable=E0611

def get_unicode(doc):
    """Return the full text of the document, utf-8 encoded"""
    start, end = doc.get_bounds()
    txt = doc.get_text(start, end, False)
    return txt.decode('utf-8')

class SpellcheckOnSave(GObject.Object, Gedit.ViewActivatable, 
                       PeasGtk.Configurable):
    """
    Performs a spellcheck on *.md,*.txt files whenever one is saved.
    """
    __gtype_name__ = "spellcheckonsave"
    view = GObject.property(type=Gedit.View)
    SETTINGS_KEY = "gedit.plugins.spellcheckonsave.py"
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._doc = None
        self._spell_error_tag = None
        self._handler_ids = []
        self._settings = Gio.Settings.new(self.SETTINGS_KEY)
        self._file_pattern = self._settings.get_string("extensions").split(';')
        self._checker = enchant.Dict(self._settings.get_string("dictionary"))
        self._word_re = re.compile(self._settings.get_string("wordregex"))
    
    def do_activate(self):
        """called when plugin is activated"""
        self._doc = self.view.get_buffer()
        self._spell_error_tag = self._doc.create_tag("spell_error", 
                                    underline=Pango.Underline.ERROR)
        self._handler_ids.append(self._doc.connect("save", self.on_save))
        self._handler_ids.append(self._doc.connect("changed", self.on_changed))
    
    def do_deactivate(self):
        """called when plugin is deactivated, cleanup"""
        for _id in self._handler_ids:
            self._doc.disconnect(_id)
    
    def do_update_state(self):
        """state requires update"""
        pass
        
    def on_changed(self, doc):
        """called when documents contents have changed"""
        istart = doc.get_iter_at_line(0)
        iend = doc.get_iter_at_line(sys.maxint)
        self._doc.remove_tag_by_name("spell_error", istart, iend)
    
    def on_save(self, doc, location, *args, **kwargs):
        """called when document is saved"""
        # pylint: disable=W0613
        (_, ext) = os.path.splitext(location.get_path())
        if ext in self._file_pattern:
            for match in self._word_re.finditer(get_unicode(doc)):
                if match.group().strip() != u'':
                    if not self._checker.check(match.group().strip()):
                        self.apply_error_tag(doc, match.start(), match.end())
    
    def apply_error_tag(self, doc, start, end):
        """apply the error tag to the text between start and end"""
        istart = doc.get_iter_at_offset(start)
        iend = doc.get_iter_at_offset(end)
        doc.apply_tag(self._spell_error_tag, istart, iend)
        
    @staticmethod
    def get_dictionaries():
        """returns a list with all the available enchant dictionary names"""
        _dicts = []
        for dict_name, _ in enchant.list_dicts():
            _dicts.append(dict_name)
        return _dicts
    
    def get_dict_index(self, text):
        """Returns the index of the dictionary name in the list"""
        for index, value in enumerate(self.get_dictionaries()):
            if text == value:
                return index
        return 0
    
    def do_create_configure_widget(self):
        """setup the config dialog"""
        # setup a check button and associate it with a GSettings key
        extlbl = Gtk.Label("Extensions:")
        extensions = Gtk.Entry()
        extensions.set_tooltip_text("Semi-colon delimited list of extensions.")
        extensions.set_text(self._settings.get_string("extensions"))
        self._settings.connect("changed::extensions", 
                               self.on_extensions_changed, extensions)
        extensions.connect('focus-out-event', self.on_extensions_focus_out)
        
        dictlbl = Gtk.Label("Dictionary:")
        dictionary = Gtk.ComboBoxText()
        dictionary.set_tooltip_text("The dictionary to use")
        dictionary.set_entry_text_column(0)
        for dict_name, _ in enchant.list_dicts():
            dictionary.append_text(dict_name)
        dictionary.set_active(
            self.get_dict_index(self._settings.get_string("dictionary")))
        self._settings.connect("changed::dictionary", 
                               self.on_dictionary_changed, dictionary)
        dictionary.connect("changed", self.on_dictionary_ctrl_changed)
        
        wordlbl = Gtk.Label("Word Regex:")
        wordregex = Gtk.Entry()
        wordregex.set_tooltip_text(
            "The regex used to determine a valid word to be spell checked.")
        wordregex.set_text(self._settings.get_string("wordregex"))
        self._settings.connect("changed::wordregex", 
                               self.on_wordregex_changed, wordregex)
        wordregex.connect('focus-out-event', self.on_wordregex_focus_out)
        
        extbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        extbox.pack_start(extlbl, False, False, 0)
        extbox.pack_start(extensions, True, True, 0)
        
        dictbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dictbox.pack_start(dictlbl, False, False, 0)
        dictbox.pack_start(dictionary, True, True, 0)
        
        wordbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        wordbox.pack_start(wordlbl, False, False, 0)
        wordbox.pack_start(wordregex, True, True, 0)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.pack_start(extbox, False, False, 0)
        vbox.pack_start(dictbox, False, False, 0)
        vbox.pack_start(wordbox, False, False, 0)
        
        return vbox
    
    @staticmethod
    def on_extensions_changed(settings, key, extensions): 
        """callback, when settings extensions value is changed, 
        set extensions controls text"""
        # pylint: disable=W0613
        extensions.set_text(settings.get_string("extensions"))
    
    def on_extensions_focus_out(self, extensions, evnt): 
        """callback, when extensions controls text is changed, 
        set settings extensions value and reset the file pattern"""
        # pylint: disable=W0613
        self._settings.set_string("extensions", extensions.get_text())
        self._file_pattern = extensions.get_text().split(';')
        
    def on_dictionary_changed(self, settings, key, dictionary):
        """callback, when settings dictionary value is changed, 
        set dictionary controls selected value"""
        # pylint: disable=W0613
        dictionary.set_active(
            self.get_dict_index(settings.get_string("dictionary")))
    
    def on_dictionary_ctrl_changed(self, dictionary):
        """callback, when dictionary controls value is changed, 
        set settings dictionary value and reset the checker"""
        self._settings.set_string("dictionary", dictionary.get_active_text())
        self._checker = enchant.Dict(dictionary.get_active_text())
        
    @staticmethod
    def on_wordregex_changed(settings, key, wordregex): 
        """callback, when settings wordregex value is changed, 
        set wordregex controls text"""
        # pylint: disable=W0613
        wordregex.set_text(settings.get_string("wordregex"))
    
    def on_wordregex_focus_out(self, wordregex, evnt): 
        """callback, when wordregex controls text is changed, 
        set settings wordregex value and reset the word regex"""
        # pylint: disable=W0613
        self._settings.set_string("wordregex", wordregex.get_text())
        self._word_re = re.compile(wordregex.get_text())


