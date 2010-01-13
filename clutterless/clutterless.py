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
Cluterless
Remove unnecessary clutter from important conversation.

For now it only removes join/parts, more to come. See TODO.

TODO: Create a TODO.
"""
__module_name__ = "clutterless"
__module_version__ = "0.1.2"
__module_description__ = "Removes clutter from your conversations"

import string
import xchat
import time
import logging
import functools
import re
import operator
import textwrap
import os

from collections import defaultdict

DEBUG_LEVEL = logging.INFO

logger = logging.getLogger('clutterless')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(DEBUG_LEVEL)
formatter = logging.Formatter("[%(asctime)s] %(name)s{%(levelname)s}: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
fh = logging.FileHandler(os.path.expanduser('~/.xchat2/clutterless.log'), 'w')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] %(funcName)s(%(lineno)d) {%(levelname)s}: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

def remove_mirc_color(text, 
        _remove_re_sub=re.compile(re.escape("\x03") + 
                                  r"(?:(\d{1,2})(?:,(\d{1,2}))?)?").sub):
    return _remove_re_sub('', text)

class LastSeen(object):
    def __init__(self, min_users, perc_cut, data=None):
        if data is None:
            data = []
        self.min_users = min_users
        self.perc_cut = perc_cut
        self._order = data
        self.clean()

    def add(self, user):
        if user in self._order: #self._data:
            self._order.remove(user)
        self._order.append(user)
    
    def clean(self):
        ammount = int(max(len(xchat.get_list('users')) * self.perc_cut / 100.0, 
                      self.min_users))
        if len(self._order) > ammount:
            logger.debug('Cleaning %r from last seen, limit %r', 
                         self._order[:-ammount], ammount)
            del self._order[:-ammount]
    
    def rename(self, nick1, nick2):
        if nick1 in self._order:
            self._order = [nick2 if nick == nick1 else nick
                           for nick in self._order]
            return True
        return False

    def __iter__(self):
        return reversed(self._order)
    
    def __contains__(self, user):
        return user in self._order    

    def __len__(self):
        return len(self._order)

    def __repr__(self):
        return 'LastSeen(%d, %r)' % (self.ammount, self._order)

class ActiveChannel(object):
    def __init__(self, timeout=300, autoclean=True, time_func=time.time, 
                       linecut=50, minlastseen=3, perclastseen=1.5):
        logger.debug('Creating new channel tracking object...')
        self.timeout = timeout
        self.autoclean = autoclean
        self._time = time_func
        self._timeout_data = {}

        self._lastseen = LastSeen(minlastseen, perclastseen)

        self._lineno = 0
        self._lineno_data = {}
        self._linecut = linecut

        self._special = set()
        
        self._checks = (self._lastseen, self._timeout_data, self._lineno_data, 
                        self._special)

    def register(self, nick):
        """Registers a new key"""
        self._timeout_data[nick] = self._time()
        self._lineno_data[nick] = self._lineno
        self._lastseen.add(nick)
        self._lineno += 1

    def register_special(self, nick):
        self._special.add(nick)
        self.register(nick)

    def info(self):
        timeout_data = ' '.join('%s[%.2f]' % (nick, time.time() - t)
                                for nick, t
                                in sorted(self._timeout_data.iteritems(),
                                          key=operator.itemgetter(1)))
        lineno_data = ' '.join('%s[%d]' % (nick, self._lineno - t)
                               for nick, t
                               in sorted(self._lineno_data.iteritems(),
                                         key=operator.itemgetter(1)))

        lastseen_data = ','.join(self._lastseen)
        special_data = ','.join(self._special)
        
        return '* Timeout(%s)\n* Lineno(%s)\n* LastSeen(%s)\n* Special(%s)' % (
                timeout_data, lineno_data, lastseen_data, special_data)

    def clean(self):
        self._cleandict(self._timeout_data, self._time(), self.timeout)
        self._cleandict(self._lineno_data, self._lineno, self._linecut)
        self._lastseen.clean()
        self._special = set(nick for nick in self._special 
                            if any(nick in check for check in self._checks[:-1]))
                
    def _cleandict(self, d, base, cut):
        for key, value in d.items():
            value = base - value
            use_cut = cut
            if key in self._special:
                use_cut *= 5
            if value > use_cut:
                logger.debug('cleaning %s for %r>%r ', key, value, use_cut)
                del d[key]
        
    def autocleans(func):
        @functools.wraps(func)
        def _method(self, *args, **kwds):
            if self.autoclean:
                self.clean()
            return func(self, *args, **kwds)
        return _method

    @autocleans
    def __len__(self):
        return sum(len(check) for check in self._checks)

    @autocleans
    def __contains__(self, user):
        """
        checks if an user is active in the channel
        user: the user to search
        returns: True if the user has been active
        """
        return any(user in check for check in self._checks)

    def rename(self, nick1, nick2):
        changed = self._lastseen.rename(nick1, nick2)
        for d in (self._timeout_data, self._lineno_data):
            if nick1 in d:
                d[nick2] = d[nick1]
                del d[nick1]
                changed = True
        if nick1 in self._special:
            self._special.remove(nick1)
            self._special.add(nick2)
            changed = True
        return changed

    del autocleans
        
class JoinPartFilter(object):
    def __init__(self):
        logger.debug('Initializing...')
        self.active = defaultdict(ActiveChannel)
        for action in (
                    'Channel Action',
                    'Channel Action Hilight',
                    'DCC CHAT Offer',
                    'Channel Message',
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
        
        xchat.hook_print('Your Message', self.message)
        for special in (
                    'Message Send',
                    'Channel Msg Hilight',
                ):
            xchat.hook_print(special, self.special, userdata=special)
        
        xchat.hook_command('clutter', self._cmd, help=self.cmd_help())

    def _extract_nick(self, text):
        nick, sep, rest = text.partition(xchat.get_prefs('completion_suffix'))
        if sep and ' ' not in nick and rest[:1] not in string.punctuation:
            nick = remove_mirc_color(nick)
            return nick
        else:
            return None

    def _cmd(self, word, word_eol, userdata):
        logger.debug('CLUTTER command - got %r', word)
        if len(word) < 2:
            print self.cmd_help()
        else:
            cmd = getattr(self, 'cmd_' + word[1], self.cmd_help)
            try:
                result = cmd(*word[2:])
            except TypeError as e:
                result = str(e)
            if result:
                print textwrap.dedent(result).strip().replace('\n', '\r\n')
        return xchat.EAT_ALL

    def cmd_help(self, command=None):
        """
        Syntax: /CLUTTER HELP [command]

        Shows help about a command.
        """
        if command:
            try:
                result = getattr(self, 'cmd_' + command).__doc__
            except AttributeError:
                result = None
            if result is None:
                result = 'clutterless: Help not found for %r' % command
            return result
        else:
            return ('clutterless: Commands available:\n\n' + 
                    ', '.join(cmd[4:] for cmd in dir(self) 
                             if cmd.startswith('cmd_')))
        
    def cmd_info(self):
        """
        Syntax: /CLUTTER INFO

        Shows clutterless stored information about current channel.
        """
        channel = self._get_channel()
        if self.active[channel]:
            data = self.active[channel].info()           
            return 'clutterless data for [%s]:\n%s' % ('@'.join(reversed(channel)), 
                                                       data)
        else:
            return 'clutterless: No data on [%s]' % '@'.join(reversed(channel))

    def cmd_debug(self, level):
        """
        Syntax: /CLUTTER DEBUG {CRITICAL|ERROR|WARNING|INFO|DEBUG}

        Sets the level of the debug logger
        """
        ch.setLevel(logging.getLevelName(level))
        return "clutterless: changing debug level to %r" % level

    def _get_channel(self):
        info = xchat.get_context().get_info
        return tuple(info(t) for t in ('host', 'channel'))
    
    def message(self, word, word_eol, user):
        """People you talk to becomes *special* - can have more timeout"""
        nick = self._extract_nick(word[1])
        if nick:
            # a nick, register as special
            channel = self._get_channel()
            activechan = self.active[self._get_channel()]
            logger.debug('Talked to %r on %s, registering as special', nick, 
                         '@'.join(reversed(channel)))
            activechan.register_special(nick)

    def special(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])  
        channel = self._get_channel()
        activechan = self.active[channel]
        logger.debug("%r(%d) special register on %s for %r: %r", userdata, 
                     activechan._lineno, '@'.join(reversed(channel)), nick, 
                     word[1:])
        activechan.register_special(nick)

    def action(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])
        channel = self._get_channel()
        activechan = self.active[channel]
        logger.debug("%r(%d) register on %s for %r: %r", userdata, 
                     activechan._lineno, '@'.join(reversed(channel)), nick, 
                     word[1:])
        activechan.register(nick)

    def supress(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])
        channel = self._get_channel()
        if nick in self.active[channel]:
            logger.debug("Allowing %s on %s: %r", userdata, 
                         '@'.join(reversed(channel)), word)
        else:
            logger.debug("Supressing %r on %s: %r", userdata, 
                         '@'.join(reversed(channel)), word)
            return xchat.EAT_XCHAT

    def rename(self, word, word_eol, userdata):
        nick1 = remove_mirc_color(word[0])
        nick2 = remove_mirc_color(word[1])
        changes = 0
        # rename happens serverwide
        thishost = xchat.get_context().get_info('host')
        for (host, channel), active in self.active.iteritems():
            if host == thishost:
                if active.rename(nick1, nick2):
                    changes += 1
        logger.debug("Renaming %r to %r on %s - %d channels changed",
                     nick1, nick2, thishost, changes)


plugin = JoinPartFilter()
