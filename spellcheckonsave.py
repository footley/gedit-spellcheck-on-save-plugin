"""
A gedit plugin which performs a spellcheck on *.md,*.txt files whenever one is 
saved.
"""

import re
import os
import enchant
from gi.repository import GObject, Gtk, Gedit, Gio # pylint: disable=E0611
from gi.repository import Pango, PeasGtk # pylint: disable=E0611

def lazyprop(func):
    """
    automagically makes a function lazy loading and behave like an attribute
    """
    attr_name = '_lazy_' + func.__name__
    @property
    def _lazyprop(self):
        """
        inner
        """
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    return _lazyprop

class Preferences(object):
    """Class for retrieving user preferences"""

    def __init__(self):
        self.settings_key = "gedit.plugins.spellcheckonsave.py"
        self._settings = Gio.Settings.new(self.settings_key)
        
    def connect(self, name, callback, *user_data):
        """connect to settings signal"""
        return self._settings.connect(name, callback, *user_data)
        
    def get_extensions(self):
        """return extensions string"""
        return self._settings.get_string("extensions")
        
    def set_extensions(self, value):
        """set extensions string"""
        return self._settings.set_string("extensions", value)
        
    def get_dictionary(self):
        """return dictionary string"""
        return self._settings.get_string("dictionary")
        
    def set_dictionary(self, value):
        """set dictionary string"""
        return self._settings.set_string("dictionary", value)
        
    def get_wordregex(self):
        """return wordregex string"""
        return self._settings.get_string("wordregex")
        
    def set_wordregex(self, value):
        """set wordregex string"""
        return self._settings.set_string("wordregex", value)
    
    @lazyprop
    def file_pattern(self):
        """return a list of file extensions"""
        return self._settings.get_string("extensions").split(';')
    
    @lazyprop
    def checker(self):
        """return a enchant dictionary for the user configured culture"""
        return enchant.Dict(self._settings.get_string("dictionary"))
    
    @lazyprop
    def wordregex(self):
        """returns the regex used to find all words"""
        return re.compile(self._settings.get_string("wordregex"))
    

class SpellcheckOnSave(GObject.Object, Gedit.ViewActivatable, 
                       PeasGtk.Configurable):
    """
    Performs a spellcheck on *.md,*.txt files whenever one is saved.
    """
    __gtype_name__ = "spellcheckonsave"
    view = GObject.property(type=Gedit.View)
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._doc = None
        self._spell_error_tag = None
        self._mark_click = None
        self._handlers = []
        self._prefs = Preferences()
    
    def do_activate(self):
        """called when plugin is activated"""
        self._doc = self.view.get_buffer()
        self._spell_error_tag = self._doc.create_tag("spell_error", 
                                    underline=Pango.Underline.ERROR)
        
        start, _ = self._doc.get_bounds()
        self._mark_click = self._doc.create_mark(
            'spc-click', start, True)
        
        self._handlers.append((self._doc, 
            self._doc.connect("save", self.on_save)))
        self._handlers.append((self.view, 
            self.view.connect('button-press-event', self.on_button_press)))
        self._handlers.append((self.view,
            self.view.connect('populate-popup', self.on_populate_popup)))
    
    def do_deactivate(self):
        """called when plugin is deactivated, cleanup"""
        for obj, _id in self._handlers:
            obj.disconnect(_id)
    
    def do_update_state(self):
        """state requires update"""
        pass
        
    def on_button_press(self, view, event):
        """
        callback for right-click
        move _mark_click to the position of the click
        """
        # pylint: disable=W0613
        if event.button == 3:
            coordx, coordy = self.view.window_to_buffer_coords(
                2, int(event.x), int(event.y))
            _iter = self.view.get_iter_at_location(coordx, coordy)
            self._doc.move_mark(self._mark_click, _iter)
        return False
    
    def on_populate_popup(self, view, menu):
        """add spelling suggestions to context menu"""
        # pylint: disable=W0613
        if self._mark_inside_word(self._mark_click):
            start, end = self._word_extents_from_mark(self._mark_click)
            if start.has_tag(self._spell_error_tag):
                word = self._doc.get_text(start, end, False)
                self._build_suggestion_menu(menu, word)
                
    def _mark_inside_word(self, mark):
        """is the supplied mark, inside of a word?"""
        _iter = self._doc.get_iter_at_mark(mark)
        return _iter.inside_word()
        
    def _word_extents_from_mark(self, mark):
        """return (start, end) tuple giving position of word in document"""
        start = self._doc.get_iter_at_mark(mark)
        if not start.starts_word():
            start.backward_word_start()
        end = self._clone_iter(start)
        if end.inside_word():
            end.forward_word_end()
        return start, end
        
    def _clone_iter(self, _iter):
        """clone the iterator"""
        return self._doc.get_iter_at_offset(_iter.get_offset())
        
    def _build_suggestion_menu(self, menu, word):
        """build the suggestion submenu"""
        suggestions = self._prefs.checker.suggest(word)
        item = Gtk.MenuItem(label='--------------------------------------')
        menu.append(item)
        if not suggestions:
            item = Gtk.MenuItem(label='No suggestions')
            menu.append(item)
        else:
            for suggestion in suggestions:
                item = Gtk.MenuItem(label=suggestion)
                item.connect('activate', self.on_replace_word, word, suggestion)
                menu.append(item)
            item = Gtk.MenuItem(label='--------------------------------------')
            menu.append(item)
            item = Gtk.MenuItem(label='Add "{0}" to dictionary'.format(word))
            item.connect('activate', self.on_add_to_dictionary, word)
            menu.append(item)
        menu.show_all()
        return menu
    
    def _replace_word_at_mark(self, newword):
        """
        replace the word at the position last clicked with the newword provided
        """
        start, end = self._word_extents_from_mark(self._mark_click)
        offset = start.get_offset()
        self._doc.begin_user_action()
        self._doc.delete(start, end)
        self._doc.insert(self._doc.get_iter_at_offset(offset), newword)
        self._doc.end_user_action()
    
    def on_add_to_dictionary(self, item, word):
        """
        Add the word to the user dictionary
        """
        # pylint: disable=W0613
        self._replace_word_at_mark(word)
        self._prefs.checker.add_to_pwl(word)
        
    def on_replace_word(self, item, oldword, newword):
        """
        suggestion submenu callback, replaces the selected word with the 
        chosen suggestion
        """
        # pylint: disable=W0613
        self._replace_word_at_mark(newword)
        self._prefs.checker.store_replacement(oldword, newword)
    
    def _get_unicode(self):
        """Return the full text of the document, utf-8 encoded"""
        start, end = self._doc.get_bounds()
        txt = self._doc.get_text(start, end, False)
        return txt.decode('utf-8')
    
    def on_save(self, doc, location, *args, **kwargs):
        """called when document is saved"""
        # pylint: disable=W0613
        (_, ext) = os.path.splitext(location.get_path())
        if ext in self._prefs.file_pattern:
            for match in self._prefs.wordregex.finditer(self._get_unicode()):
                if match.group().strip() != u'':
                    if not self._prefs.checker.check(match.group().strip()):
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
        extensions.set_text(self._prefs.get_extensions())
        self._prefs.connect("changed::extensions", 
                               self.on_extensions_changed, extensions)
        extensions.connect('focus-out-event', self.on_extensions_focus_out)
        
        dictlbl = Gtk.Label("Dictionary:")
        dictionary = Gtk.ComboBoxText()
        dictionary.set_tooltip_text("The dictionary to use")
        dictionary.set_entry_text_column(0)
        for dict_name, _ in enchant.list_dicts():
            dictionary.append_text(dict_name)
        dictionary.set_active(
            self.get_dict_index(self._prefs.get_dictionary()))
        self._prefs.connect("changed::dictionary", 
                               self.on_dictionary_changed, dictionary)
        dictionary.connect("changed", self.on_dictionary_ctrl_changed)
        
        wordlbl = Gtk.Label("Word Regex:")
        wordregex = Gtk.Entry()
        wordregex.set_tooltip_text(
            "The regex used to determine a valid word to be spell checked.")
        wordregex.set_text(self._prefs.get_wordregex())
        self._prefs.connect("changed::wordregex", 
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
        self._prefs.set_extensions(extensions.get_text())
        
    def on_dictionary_changed(self, settings, key, dictionary):
        """callback, when settings dictionary value is changed, 
        set dictionary controls selected value"""
        # pylint: disable=W0613
        dictionary.set_active(
            self.get_dict_index(settings.get_string("dictionary")))
    
    def on_dictionary_ctrl_changed(self, dictionary):
        """callback, when dictionary controls value is changed, 
        set settings dictionary value and reset the checker"""
        self._prefs.set_dictionary(dictionary.get_active_text())
        
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
        self._prefs.set_wordregex(wordregex.get_text())


