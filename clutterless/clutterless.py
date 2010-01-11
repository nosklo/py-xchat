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

import xchat
import time
import logging
import functools
import re
import operator
from UserDict import DictMixin
from collections import deque, defaultdict

DEBUG_LEVEL = logging.INFO

logger = logging.getLogger('clutterless')
logger.setLevel(DEBUG_LEVEL)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] %(name)s{%(levelname)s}: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

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
        ammount = max(len(xchat.get_list('users')) * self.perc_cut / 100, 
                      self.min_users)
        logger.debug('Searching for last %r', ammount)
        if len(self._order) > ammount:
            logger.debug('Cleaning LastSeen %r', self._order[:-ammount])
            del self._order[:-ammount]
    
    def rename(self, nick1, nick2):
        self._order = [nick2 if nick == nick1 else nick
                       for nick in self._order]

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
                       linecut=50, minlastseen=2, perclastseen=1):
        self.timeout = timeout
        self.autoclean = autoclean
        self._time = time_func
        self._timeout_data = {}

        self._lastseen = LastSeen(minlastseen, perclastseen)

        self._lineno = 0
        self._lineno_data = {}
        self._linecut = linecut
        
        self._checks = (self._lastseen, self._timeout_data, self._lineno_data)

    def register(self, key):
        """Registers a new key"""
        self._timeout_data[key] = self._time()
        self._lineno_data[key] = self._lineno
        self._lastseen.add(key)
        self._lineno += 1

    def show(self):
        timeout_data = ' '.join('%s[%.2f]' % (nick, time.time() - t)
                                for nick, t
                                in sorted(self._timeout_data.iteritems(),
                                          key=operator.itemgetter(1)))
        lineno_data = ' '.join('%s[%d]' % (nick, self._lineno - t)
                               for nick, t
                               in sorted(self._lineno_data.iteritems(),
                                         key=operator.itemgetter(1)))

        lastseen_data = ','.join(self._lastseen)
        
        return 'Timeout(%s), Lineno(%s), LastSeen(%s)' % (timeout_data,
                                                          lineno_data,
                                                          lastseen_data)

    def clean(self):
        self._cleandict(self._timeout_data, self._time(), self.timeout)
        self._cleandict(self._lineno_data, self._lineno, self._linecut)
        self._lastseen.clean()
                
    def _cleandict(self, d, base, cut):
        for key, value in d.items():
            value = base - value
            if value > cut:
                logger.debug('cleaning %s for %r<%r ', key, value, cut)
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
        logger.debug("Renaming %r to %r", nick1, nick2)
        self._lastseen.rename(nick1, nick2)
        for d in (self._timeout_data, self._lineno_data):
            if nick1 in d:
                d[nick2] = d[nick1]
                del d[nick1]
        
class JoinPartFilter(object):
    def __init__(self):
        self.active = defaultdict(ActiveChannel)
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
        
        xchat.hook_command('clutterdebug', self.cmd_debug)
        xchat.hook_command('cluttershow', self.cmd_show)

    def _get_channel(self):
        info = xchat.get_context().get_info
        return tuple(info(t) for t in ('host', 'channel'))
        

    def action(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])
        activechan = self.active[self._get_channel()]
        logger.debug("%r(%d) register for %r: %r", userdata, activechan._lineno, 
                                                   nick, word)
        activechan.register(nick)

    def supress(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])
        if nick in self.active[self._get_channel()]:
            logger.debug("Not supressing %r: %r", userdata, word)
        else:
            logger.debug("supressing %r: %r", userdata, word)
            return xchat.EAT_XCHAT

    def rename(self, word, word_eol, userdata):
        nick1 = remove_mirc_color(word[0])
        nick2 = remove_mirc_color(word[1])
        # rename happens serverwide
        thishost = xchat.get_context().get_info('host')
        for (host, channel), active in self.active.iteritems():
            if host == thishost:
                active.rename(nick1, nick2)

    def cmd_show(self, word, word_eol, userdata):
        channel = self._get_channel()
        if self.active[channel]:
            data = self.active[channel].show()           
            logger.info('[%s] %s', '@'.join(reversed(channel)), data)
        else:
            logger.info('Nothing registered for %r', '@'.join(reversed(channel)))
        return xchat.EAT_ALL

    def cmd_debug(self, word, word_eol, userdata):
        if len(word) <= 1:
            logger.error('Need the level for %r', word[0])
        else:
            logger.info("changing debug level to %r", word[1])
            logger.setLevel(logging.getLevelName(word[1]))
        return xchat.EAT_ALL

plugin = JoinPartFilter()
