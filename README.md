Gedit Spell check on Save
=========================

A gedit plug in which and performs a spellcheck on *.txt and *.md (configurable) files whenever one is saved.

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

You can configure the extensions to be spell checked; the dictionary used and the regex used to find all words in the document in the plugins preferences.


