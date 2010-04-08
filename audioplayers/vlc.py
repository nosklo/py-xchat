#-*- coding:utf-8 -*-
__module_name__ = "VLCpy"
__module_version__ = "0.1a"
__module_description__ = "VLC XChat spam (python)"


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

import xchat
import urllib2
import os
import xml.etree.ElementTree as etree

URL = 'http://localhost:8080/requests/status.xml'

def parse_time(seconds):
    seconds = int(seconds)
    return '%d:%02d' % divmod(seconds, 60)
    
def vlc(word, word_eol, userdata):
    try:
        el = etree.parse(urllib2.urlopen(URL))
    except urllib2.URLError, e:
        print 'VLC not running or not set up correctly'
        print 'Please configure VLC to listen on http 127.0.0.1:8080'
        print 'Error was: %s' % (e,)
    else:
        if el.find('state').text != 'playing':
            print 'Not playing anything'
        else:
            d = {
                'artist': 'Unknown',
                'title': 'Unknown',
                'album': 'Unknown',
                'time': parse_time(int(el.find('time').text)),
                'length': parse_time(int(el.find('length').text)),
                }
            d.update((e.attrib['name'].lower(), e.text) 
                     for e in el.getiterator('info') 
                     if e.attrib.get('name', '').lower() in ('artist', 'title', 'album'))
            xchat.command ("say VLC> %(artist)s - %(title)s [%(time)s/%(length)s]" % d)
    return xchat.EAT_ALL

xchat.hook_command("vlc", vlc, "/vlc SPAMS")
print "=> VLC Python spam loaded"

