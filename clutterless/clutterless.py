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
__module_version__ = "0.1.3"
__module_description__ = "Removes clutter from your conversations"

import string
import time
import logging
import functools
import re
import operator
import textwrap
import os

from collections import defaultdict

try:
    import hexchat as xchat
    xchat.EAT_XCHAT = xchat.EAT_HEXCHAT
    CONFIGDIR = '~/.config/hexchat'
except ImportError:
    try:
        import xchat
        CONFIGDIR = '~/.xchat2'
    except ImportError:
        print('XChat/HexChat not found!')
        exit(1)
LOGFILE = os.path.expanduser(os.path.join(CONFIGDIR, 'clutterless.log'))
DEBUG_LEVEL = logging.INFO

logger = logging.getLogger('clutterless')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(DEBUG_LEVEL)
formatter = logging.Formatter("[%(asctime)s] %(name)s{%(levelname)s}: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
fh = logging.FileHandler(LOGFILE, 'w')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] %(funcName)s(%(lineno)d) {%(levelname)s}: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

def remove_mirc_color(text, 
        _remove_re_sub=re.compile(re.escape("\x03") + 
                                  r"(?:(\d{1,2})(?:,(\d{1,2}))?)?").sub):
    return _remove_re_sub('', text)

def split_nick(text, seps=':,'):
    seps = '|'.join(re.escape(sep) for sep in seps)
    re_nick = re.compile(r"([\D_][\w_]+)(?:%s)([\s\w].*)$" % (seps,))
    m = re_nick.match(remove_mirc_color(text))
    if m:
        return m.groups()
    return (None, None)

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
        
    def _autoclean(self):
        if self.autoclean:
            return self.clean()

    def __len__(self):
        self._autoclean()
        return sum(len(check) for check in self._checks)

    def __contains__(self, user):
        """
        checks if an user is active in the channel
        user: the user to search
        returns: True if the user has been active
        """
        self._autoclean()
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
        
class JoinPartFilter(object):
    def __init__(self):
        logger.debug('Initializing...')
        self.active = defaultdict(ActiveChannel)
        for action, args in (
                    ('Channel Action', [0]),
                    ('Channel Action Hilight', [0]),
                    ('DCC CHAT Offer', [0]),
                    ('Channel Message', [0]),
                ):
            xchat.hook_print(action, self.action, userdata=(action, args))
        for supressed, args in (
                    ('Join', [0]),
                    ('Part', [0]),
                    ('Part with Reason', [0]),
                    ('Change Nick', [0, 1]),
                    ('Quit', [0]),
                ):
            xchat.hook_print(supressed, self.supress, userdata=(supressed, args))
        
        xchat.hook_print('Change Nick', self.rename, priority=xchat.PRI_LOW)
        
        xchat.hook_print('Your Message', self.message)
        for special in (
                    'Message Send',
                    'Channel Msg Hilight',
                ):
            xchat.hook_print(special, self.special, userdata=special)
        
        xchat.hook_command('clutter', self._cmd, help=self.cmd_help())


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
        active_channel = self.active[channel]
        if active_channel is None:        
            return 'clutterless: Channel is disabled'
        elif not active_channel:
            return 'clutterless: No data on [%s]' % '@'.join(reversed(channel))
        data = self.active[channel].info()           
        return 'clutterless: data for [%s]:\n%s' % ('@'.join(reversed(channel)), 
                                                       data)

    def cmd_debug(self, level):
        """
        Syntax: /CLUTTER DEBUG {CRITICAL|ERROR|WARNING|INFO|DEBUG}

        Sets the level of the debug logger
        """
        ch.setLevel(logging.getLevelName(level))
        return "clutterless: changing debug level to %r" % level

    def cmd_enable(self):
        """
        Syntax: /CLUTTER ENABLE

        Enable clutterless filtering for the current channel
        """
        channel = self._get_channel()
        if self.active[channel] is not None:
            return 'clutterless: Channel %s is already enabled!' % (channel,)
        logger.debug("Enabling %s", channel)
        self.active[channel] = ActiveChannel()
        return 'clutterless: Now tracking channel %s' % (channel,)

    def cmd_disable(self):
        """
        Syntax: /CLUTTER DISABLE

        Disable clutterless filtering for the current channel
        """
        channel = self._get_channel()
        if self.active[channel] is None:
            return 'clutterless: Channel %s is already disabled!' % (channel,)
        logger.debug("Disabling %s", channel)
        self.active[channel] = None
        return 'clutterless: Channel %s is now disabled' % (channel,)

    def _get_channel(self):
        info = xchat.get_context().get_info
        return tuple(info(t) for t in ('host', 'channel'))
    
    def message(self, word, word_eol, user):
        """People you talk to becomes *special* - can have more timeout"""
        nick, rest = split_nick(word[1], seps=[xchat.get_prefs('completion_suffix')])
        if nick:
            # a nick, register as special
            channel = self._get_channel()
            activechan = self.active[self._get_channel()]
            if activechan is None:
                logger.debug('Channel %s is disabled, ignoring conversation', 
                    '@'.join(reversed(channel)))
                return
            logger.debug('Talked to %r on %s, registering as special', nick, 
                         '@'.join(reversed(channel)))
            activechan.register_special(nick)

    def special(self, word, word_eol, userdata):
        act = userdata
        nick = remove_mirc_color(word[0])
        channel = self._get_channel()
        activechan = self.active[channel]
        if activechan is None:
            logger.debug('Channel %s is disabled, ignoring conversation', 
                '@'.join(reversed(channel)))
            return        
        logger.debug("%r(%d) special register on %s for %r: %r", userdata, 
                     activechan._lineno, '@'.join(reversed(channel)), nick, 
                     word[1:])
        activechan.register_special(nick)

    def action(self, word, word_eol, userdata):
        act, nicks = userdata
        for nick in nicks:
            nick = remove_mirc_color(word[nick])
            channel = self._get_channel()
            activechan = self.active[channel]
            if activechan is None:
                logger.debug('Channel %s is disabled, ignoring action', 
                    '@'.join(reversed(channel)))
                return
            logger.debug("%r(%d) register on %s for %r: %r", userdata, 
                         activechan._lineno, '@'.join(reversed(channel)), nick, 
                         word[1:])
            activechan.register(nick)

    def supress(self, word, word_eol, userdata):
        act, nicks = userdata
        for nick in nicks:
            nick = remove_mirc_color(word[nick])
            channel = self._get_channel()
            activechan = self.active[channel]
            if activechan is None:
                logger.debug('Channel %s is disabled, allowing message', 
                    '@'.join(reversed(channel)))
                return xchat.EAT_NONE
            if nick in self.active[channel]:
                logger.debug("Allowing %s on %s: %r", userdata, 
                             '@'.join(reversed(channel)), word)
                return xchat.EAT_NONE
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
                if active and active.rename(nick1, nick2):
                    changes += 1
        logger.debug("Renaming %r to %r on %s - %d channels changed",
                     nick1, nick2, thishost, changes)


plugin = JoinPartFilter()
