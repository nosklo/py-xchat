#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright© 2010 Clovis Fabricio Costa

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

"""
Smartwarn
Warns you about stupid things you might be doing.
"""
__module_name__ = "smartwarn"
__module_version__ = "0.0.1"
__module_description__ = "Warns you about stupid things"

import xchat
import re
import string

last_msg = None

def _extract_nick(text):
    nick, sep, rest = text.partition(xchat.get_prefs('completion_suffix'))
    if sep and ' ' not in nick and rest[:1] not in string.punctuation:
        nick = remove_mirc_color(nick)
        return nick
    else:
        return None

def remove_mirc_color(text, 
        _remove_re_sub=re.compile(re.escape("\x03") + 
                                  r"(?:(\d{1,2})(?:,(\d{1,2}))?)?").sub):
    return _remove_re_sub('', text)

def verify_errors(word, word_eol, userdata):
    global last_msg
    nick = _extract_nick(word_eol[0])
    if word_eol[0] != last_msg:
        last_msg = word_eol[0]
        if nick == xchat.get_info('nick'):
            print 'WARNING: Sending message to yourself - Repeat to confirm.'
            return xchat.EAT_ALL
        elif nick and all(nick != user.nick for user in xchat.get_list('users')):
            print 'WARNING: %r is not here. Repeat to confirm.' % nick
            return xchat.EAT_ALL

xchat.hook_command('', verify_errors)

