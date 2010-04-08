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

"""
Channelread
Allows you to enable/disable audio reading for a specific channel
"""
__module_name__ = "channelread"
__module_version__ = "0.0.2"
__module_description__ = "Allows enabling/disabling text-to-speech on each channel"

import xchat
import subprocess
import os
import textwrap
import re

def remove_mirc_color(text, 
        _remove_re_sub=re.compile(re.escape("\x03") + 
                                  r"(?:(\d{1,2})(?:,(\d{1,2}))?)?").sub):
    return _remove_re_sub('', text)

class TextToSpeech(object):
    def __init__(self):
        self._enabled = {}
        for action in (
                    'Channel Action',
                    'Channel Action Hilight',
                    'Channel Message',
                    'Channel Msg Hilight',
                ):
            xchat.hook_print(action, self.message, action)
        xchat.hook_command('audio', self._cmd, help=self.cmd_help())
        xchat.hook_unload(self.kill)
        self.p = None
        self.voice = 'en-us'
        self.speed = 170
        self.pitch = 50
        
    def relaunch(self):
        self.kill()
        devnull = open(os.devnull, 'w+b')
        self.p = subprocess.Popen(['espeak', '-v', self.voice, 
                                             '-p', str(self.pitch),
                                             '-s', str(self.speed)],
                                   stdin=subprocess.PIPE,
                                   stdout=devnull, stderr=devnull,
                                   close_fds=True)

    def _cmd(self, word, word_eol, userdata):
        if len(word) < 2:
            print self.cmd_help()
        else:
            cmd = getattr(self, 'cmd_' + word[1].lower(), self.cmd_help)
            try:
                result = cmd(*word[2:])
            except TypeError as e:
                result = str(e)
            if result:
                print textwrap.dedent(result).strip().replace('\n', '\r\n')
        return xchat.EAT_ALL

    def kill(self, data=None):
        if self.p is not None and self.p.poll() is None:
            self.p.stdin.close()
            self.p.kill()
            self.p.wait()

    def cmd_help(self, command=None, *extra):
        """
        Syntax: /AUDIO HELP [command]

        Shows help about a command.
        """
        if command:
            try:
                result = getattr(self, 'cmd_' + command.lower()).__doc__
            except AttributeError:
                result = None
            if result is None:
                result = 'channelread: Help not found for %r' % command
            return result
        else:
            return ('channelread: Commands available:\n\n' + 
                    ', '.join(cmd[4:] for cmd in dir(self) 
                             if cmd.startswith('cmd_')))
        
    def cmd_on(self, voice):
        """
        Syntax: /AUDIO ON [voice]
        
        Turns on audio speech for a channel.
        """
        chan = self._get_channel()
        if chan in self._enabled:
            return 'ERROR: Audio speech is already enabled for %s' % chan
        self._enabled.add(chan)
        return 'Audio speech enabled for %s' % chan
    
    def cmd_off(self):
        """
        Syntax: /AUDIO OFF
        
        Turns off audio speech for a channel.
        """
        chan = self._get_channel()
        if chan not in self._enabled:
            return 'ERROR: Audio speech is not enabled for %s' % chan
        self._enabled.remove(chan)
        return 'Audio speech disabled for %s' % chan
        
    def cmd_speed(self, new_speed=None):
        """
        Syntax: /AUDIO SPEED [NEW_SPEED]
        
        Defines speed in words per minute, 80 to 390;
        Without parameters shows current setting.
        """
        
        if new_speed is None:
            return 'Current speed: %d' % self.speed
        else:
            self.speed = int(new_speed)
            self.relaunch()
            return 'Speed set to %d' % self.speed
            
    def cmd_pitch(self, new_pitch=None):
        """
        Syntax: /AUDIO PITCH [NEW_PITCH]
        
        Defines pitch adjustment, 0 to 99
        Without parameters shows current setting.
        """
        if new_pitch is None:
            return 'Current pitch: %d' % self.pitch
        else:
            self.pitch = int(new_pitch)
            self.relaunch()
            return 'Pitch set to %d' % self.pitch

    def cmd_voice(self, new_voice=None):
        """
        Syntax: /AUDIO VOICE [NEW_PITCH]
        
        Use voice file of this name from espeak-data/voices
        Without parameters shows current setting.
        """
        
        if new_voice is None:
            return 'Current voice: %r' % self.voice
        else:
            self.voice = new_voice
            self.relaunch()
            return 'Voice set to %r' % self.voice
    
    def cmd_list(self):
        """
        Syntax: /AUDIO LIST
        
        Lists channels where text reading is enabled
        """
        if self._enabled:
            return 'Speech is enabled for %s' % ', '.join(repr(x) 
                                                for x in self._enabled)
        return 'No channel has speech enabled'
        
    def message(self, word, word_eol, userdata):
        """Got message, speaking"""
        chan = self._get_channel()
        if chan in self._enabled:
#            print 'DEBUG: speaking %r' % word_eol[1]
            self.speak(word_eol[1])    
        return xchat.EAT_NONE

    def _get_channel(self):
        info = xchat.get_context().get_info
        return '@'.join(info(t) for t in ('channel', 'host'))

    def speak(self, msg):
        if self.p is None or self.p.poll() is not None:
            self.relaunch()
        self.p.stdin.write(remove_mirc_color(msg) + '\n')
        self.p.stdin.flush()

plugin = TextToSpeech()
print 'Plugin %s loaded - for help use /AUDIO HELP' % (__module_name__,)
