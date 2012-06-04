Gedit Spell check on Save
=========================

A Gedit plug in which and performs a spell-check on *.txt and *.md (configurable) files whenever one is saved.

Right-click on misspelled words and use Suggestions sub-menu to change.

Installation
------------

Either run the script ``./install.sh`` provided or:

1. Install enchant ``pip install pyenchant``
2. copy the gschema file to the correct folder. 
   ``cp spellcheckonsave.gschema.xml /usr/share/glib-2.0/schemas/``
   ``glib-compile-schemas /usr/share/glib-2.0/schemas/``
3. Copy ``spellcheckonsave.plugin`` and ``spellcheckonsave.py`` to ``~/.local/share/gedit/plugins`` then activate from Gedit's plugins dialog.

Configuration
-------------

You can configure the extensions to be spell checked; the dictionary used and the reg-ex used to find all words in the document in the plug-ins preferences.
