#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright© 2009-2010 Clovis Fabricio Costa

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__module_name__ = "hybrid_decode"
__module_version__ = "0.0.1"
__module_description__ = "Charset conversion script"

FALLBACK = 'cp1255'

import xchat

def _force_unicode(text):
    try:
        result = text.decode('utf-8')
    except UnicodeDecodeError:
        result = text.decode(FALLBACK)
    return result

def _convert_piece(text):
    text = text.decode('utf-8')
    try:
        result = text.encode('latin1').decode(FALLBACK).encode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        result = text.encode('utf-8')
    return result

ignore = False

def convert_chars(word, word_eol, user_data):
    global ignore
    if not ignore:
        print word
        word = [_convert_piece(w) for w in word]
        ignore = True
        xchat.emit_print(user_data, *word)
        ignore = False
        return xchat.EAT_ALL
        
for act in (
        'Channel Action',
        'Channel Action Hilight',
        'Channel Message',
        'Channel Msg Hilight',
        ):
    xchat.hook_print(act, convert_chars, act, priority=xchat.PRI_HIGHEST)
    

