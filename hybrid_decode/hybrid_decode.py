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

CHARSETS_8BIT = set(['437', '850', '852', '855', '860', '861', '862', '863', 
                     '865', '866', '8859', 'cp-is', 'cp037', 'cp1026', 
                     'cp1140', 'cp1256', 'cp154', 'cp437', 'cp500', 'cp737', 
                     'cp775', 'cp819', 'cp850', 'cp852', 'cp855', 'cp860', 
                     'cp861', 'cp862', 'cp863', 'cp865', 'cp866', 'csptcp154', 
                     'cyrillic', 'cyrillic-asian', 'ebcdic-cp-be', 
                     'ebcdic-cp-ch', 'ibm037', 'ibm039', 'ibm1026', 'ibm1140', 
                     'ibm437', 'ibm500', 'ibm775', 'ibm850', 'ibm852', 
                     'ibm855', 'ibm860', 'ibm861', 'ibm862', 'ibm863', 
                     'ibm865', 'ibm866', 'iso-8859-1', 'iso-8859-10', 
                     'iso-8859-13', 'iso-8859-14', 'iso-8859-15', 'iso-8859-2', 
                     'iso-8859-4', 'iso-8859-5', 'iso-8859-9', 'iso8859-1', 
                     'iso8859_10', 'iso8859_13', 'iso8859_14', 'iso8859_15', 
                     'iso8859_2', 'iso8859_4', 'iso8859_5', 'iso8859_9', 
                     'koi8_r', 'koi8_u', 'l1', 'l2', 'l4', 'l5', 'l6', 'l8', 
                     'latin', 'latin1', 'latin2', 'latin4', 'latin5', 
                     'latin6', 'latin8', 'latin_1', 'mac_cyrillic', 
                     'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman', 
                     'mac_turkish', 'maccentraleurope', 'maccyrillic', 
                     'macgreek', 'maciceland', 'maclatin2', 'macroman', 
                     'macturkish', 'pt154', 'ptcp154', 'windows-1256'])

MSG_WRONGENC =("hybrid: CHARSET is %r which doesn't support full 8bit "
               "encoding for %r. Can't convert this message. Setting the "
               'CHARSET to latin1 now so it can work from now on.\r\n'
               'Configure xchat to any 8bit encoding using either '
               '/CHARSET <encoding> or the server preferences window '
               'before loading the plugin to prevent this message on the '
               'future.')

EVENTS = [
  ("Channel Action", [1]),
  ("Channel Action Hilight", [1]),
  ("Channel Message", [1]),
  ("Channel Msg Hilight", [1]),
  ("Channel Notice", [2]),
  ("Generic Message", [0, 1]),
  ("Kick", [3]),
  ("Killed", [1]),
  ("Motd", [0]),
  ("Notice", [1]),
  ("Part with Reason", [3]),
  ("Private Message", [1]),
  ("Private Message to Dialog", [1]),
  ("Quit", [1]),
  ("Receive Wallops", [1]),
  ("Server Notice", [0]),
  ("Server Text", [0]),
  ("Topic", [1]),
  ("Topic Change", [1]),
]

import xchat

class Plugin(object):
    def __init__(self):
#        self._server_charset = {}
        self.fallbacks = ['cp1255'] # that will be configurable and user-settable.
        self._ignore_receive = False
        self._ignore_send = False
        for event in EVENTS:
            xchat.hook_print(event[0], self.convert, event, 
                             priority=xchat.PRI_HIGHEST)
#        xchat.hook_command('', self.debug_print, 'all', priority=xchat.PRI_HIGHEST)
        xchat.hook_command('', self.fix_sends, priority=xchat.PRI_HIGHEST)
        for cmd in ('SAY', 'ME', 'MSG'):
            xchat.hook_command(cmd, self.fix_sendcmd, cmd, priority=xchat.PRI_HIGHEST)
#        xchat.hook_command('SAY', self.fix_sends_say, priority=xchat.PRI_HIGH)
        
    def _convert_piece(self, text, used_charset):
        raw = text.decode('utf-8').encode(used_charset)
        try:
            result = raw.decode('utf-8')
        except UnicodeDecodeError:
            for encoding in self.fallbacks:
                try:
                    result = raw.decode(encoding)
                except UnicodeDecodeError:
                    pass
                else:
                    break
            else:
                result = raw.decode(used_charset)
        return result.encode('utf-8')
                
    def convert(self, word, word_eol, userdata):
        if self._ignore_receive:
            return
        event, pos = userdata
        charset = xchat.get_info('charset')
        if charset and charset.lower() in CHARSETS_8BIT:
            for p in pos:
                word[p] = self._convert_piece(word[p], charset)
            self._ignore_receive = True
            xchat.emit_print(event, *word)
            self._ignore_receive = False
            return xchat.EAT_ALL
        else:
            host = xchat.get_info('host')
            print MSG_WRONGENC % (charset, host)
            xchat.command('CHARSET latin1')
#            self._server_charset[host] = charset

    def debug_print(self, word, word_eol, user_data):
        self._ignore_debug = True
        if word_eol[0]:
            print user_data, repr(word_eol[0])
        else:
            print user_data, '-> empty event!'
        self._ignore_debug = False

    def fix_sendcmd(self, word, word_eol, user_data):
        if self._ignore_send or len(word_eol) < 2:
            return
        charset = xchat.get_info('charset')
        xchat.command('CHARSET -quiet UTF-8')
        self._ignore_send = True
        xchat.command('%s %s' % (word[0], word_eol[1]))
        self._ignore_send = False
        xchat.command('CHARSET -quiet ' + charset)
        return xchat.EAT_ALL
        
    def fix_sends(self, word, word_eol, user_data):
        if self._ignore_send:
            return
        word = ['SAY']
        word_eol = [None, word_eol[0]]
        return self.fix_sendcmd(word, word_eol, user_data)

#    def fix_sends(self, word, word_eol, user_data):
#        if self._ignore:
#            return
#        charset = xchat.get_info('charset')
#        # change whatever is being sent to double-encoded utf-8
#        if charset and charset.lower() in CHARSETS_8BIT:
#            word_eol = word_eol[0].decode(charset).encode('utf-8')
#            self._ignore = True
#            xchat.command('SAY ' + word_eol)
#            self._ignore = False
#            return xchat.EAT_ALL
#        else:
#            host = xchat.get_info('host')
#            print MSG_WRONGENC % (charset, host)
#            xchat.command('CHARSET latin1')

    def fix_sends_say(self, word, word_eol, user_data):
        if self._ignore:
            return
        return self.fix_sends([], word_eol[1:], user_data)

p = Plugin()

#def _convert_piece(text):
#    text = text.decode('utf-8')
#    try:
#        result = text.encode('latin1').decode(FALLBACK).encode('utf-8')
#    except (UnicodeEncodeError, UnicodeDecodeError):
#        result = text.encode('utf-8')
#    return result

#ignore = False

#def convert_chars(word, word_eol, user_data):
#    global ignore
#    if not ignore:
#        print word
#        word = [_convert_piece(w) for w in word]
#        ignore = True
#        xchat.emit_print(user_data, *word)
#        ignore = False
#        return xchat.EAT_ALL
#        
#for act in (
#        'Channel Action',
#        'Channel Action Hilight',
#        'Channel Message',
#        'Channel Msg Hilight',
#        ):
#    xchat.hook_print(act, convert_chars, act, priority=xchat.PRI_HIGHEST)
#    


#xchat.hook_server("PRIVMSG", print_me)


