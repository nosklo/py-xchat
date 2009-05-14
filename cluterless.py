#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright© 2009 Clovis Fabricio Costa

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
Cluterless
Remove unnecessary clutter from important conversation.

For now it only removes join/parts, more to come. See TODO.

TODO: Create a TODO.
"""
__module_DEBUG__ = False
__module_name__ = "clutterless" 
__module_version__ = "0.1" 
__module_description__ = "Removes clutter from your conversations" 

import xchat
import time

def debug(info):
    if __module_DEBUG__:
        print info

class JoinPartFilter(object):
    def __init__(self, timeout=120):
        self.timeout = timeout
        self.actions = {}
        for action in (
                    'Channel Action',
                    'Channel Action Hilight',
                    'DCC CHAT Offer',
                    'Message Send',
                    'Channel Message',
                    'Channel Msg Hilight',
                ):
            xchat.hook_print(action, self.action, userdata=action)
        for supressed in (
                    'Join',
                    'Part',
                    'Part with Reason',
                    'Change Nick',
                    'Quit',
                ):
            xchat.hook_print(supressed, self.supress, userdata=supressed)
        xchat.hook_print('Change Nick', self.rename, priority=xchat.PRI_LOW)

    def fix_nick(self, nick):
        while nick.startswith('\x03'):
            nick = nick[3:]
        return nick

    def action(self, word, word_eol, userdata): 
        nick = self.fix_nick(word[0])
        self.actions[nick] = time.time()
        debug("action for %r registered: %r, %r" % (nick, word, userdata))
        
    def timed_out(self, nick):
        now = time.time()
        return now - self.actions.get(nick, 0) >= self.timeout
    
    def supress(self, word, word_eol, userdata):
        nick = self.fix_nick(word[0])
        if self.timed_out(nick):
            debug("supressing %r: %r" % (userdata, word))
            return xchat.EAT_XCHAT
        else:
            debug("Not supressing %r: %r" % (userdata, word))
    
    def rename(self, word, word_eol, userdata):
        nick1 = self.fix_nick(word[0])
        nick2 = self.fix_nick(word[1])
        if nick1 in self.actions:
            self.actions[nick2] = self.actions[nick1]
            del self.actions[nick1]
            
plugin = JoinPartFilter()

