#!/bin/bash

echo install pyenchant
pip install pyenchant

echo copy settings schema and compile
cp spellcheckonsave.gschema.xml /usr/share/glib-2.0/schemas/
glib-compile-schemas /usr/share/glib-2.0/schemas/

echo remove any old version
rm ~/.local/share/gedit/plugins/spellcheckonsave.*

echo copy plugin files
cp spellcheckonsave.plugin ~/.local/share/gedit/plugins/
cp spellcheckonsave.py ~/.local/share/gedit/plugins/
