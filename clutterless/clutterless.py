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
__module_name__ = "clutterless"
__module_version__ = "0.1.1"
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

_regex_mirc_color = re.compile("\x03(?:(\d{1,2})(?:,(\d{1,2}))?)?")

def remove_mirc_color(text):
    return _regex_mirc_color.sub('', text)

class TimeoutChecker(DictMixin, dict):
    def __init__(self, timeout, autoclean=True, time_func=time.time):
        self.timeout = timeout
        self.autoclean = autoclean
        self._time = time_func

    def register(self, key):
        """Registers a new key"""
        self[key] = self._time()

    def clean(self):
        now = self._time()
        for key in self.keys():
            t = now - dict.__getitem__(self, key)
            if  t > self.timeout:
                logger.debug('cleaning %s for %r ' % (key, t))
                del self[key]

    def autocleans(func):
        @functools.wraps(func)
        def _method(self, *args, **kwds):
            if self.autoclean:
                self.clean()
            return func(self, *args, **kwds)
        return _method

    @autocleans
    def __contains__(self, key):
        """
        checks if a key has timed out or not
        key: the key to search
        returns: True if the key is still active, False if it timed out.
        """
        return dict.__contains__(self, key)

    @autocleans
    def __getitem__(self, key):
        return dict.__getitem__(self, key)

class JoinPartFilter(object):
    def __init__(self, timeout=300):
        self.active = defaultdict(lambda: TimeoutChecker(timeout))
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

    def action(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])
        channel = xchat.get_context().get_info('channel')
        self.active[channel].register(nick)
        logger.debug("action for %r registered: %r, %r", nick, word, userdata)

    def supress(self, word, word_eol, userdata):
        nick = remove_mirc_color(word[0])
        channel = xchat.get_context().get_info('channel')
        if nick in self.active[channel]:
            logger.debug("Not supressing %r: %r", userdata, word)
        else:
            logger.debug("supressing %r: %r", userdata, word)
            return xchat.EAT_XCHAT

    def rename(self, word, word_eol, userdata):
        nick1 = remove_mirc_color(word[0])
        nick2 = remove_mirc_color(word[1])
        channel = xchat.get_context().get_info('channel')
        if nick1 in self.active[channel]:
            logger.debug("Renaming %r to %r", nick1, nick2)
            self.active[channel][nick2] = self.active[channel][nick1]
            del self.active[channel][nick1]

    def cmd_show(self, word, word_eol, userdata):
        channel = xchat.get_context().get_info('channel')
        if self.active[channel]:
            data = ' '.join('%s[%.2f]' % (nick, time.time() - t)
                            for nick, t
                            in sorted(self.active[channel].iteritems(),
                                      key=operator.itemgetter(1)))
            logger.info('[%s] %s' % (channel, data))
        else:
            logger.info('Nothing registered for %r' % (channel,))
        return xchat.EAT_ALL

    def cmd_debug(self, word, word_eol, userdata):
        if len(word) <= 1:
            logger.error('Need the level for %r', word[0])
        else:
            logger.info("changing debug level to %r", word[1])
            logger.setLevel(logging.getLevelName(word[1]))
        return xchat.EAT_ALL

plugin = JoinPartFilter()
