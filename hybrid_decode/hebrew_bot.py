import sys
from twisted.internet import reactor, task, defer, protocol
from twisted.python import log
from twisted.words.protocols import irc
from twisted.application import internet, service

import re

HOST, PORT = 'irc.freenode.net', 6667

class MyFirstIRCProtocol(irc.IRCClient):
    nickname = 'hebrew_bot'
    
    # This is called once the server has acknowledged that we sent
    # both NICK and USER.
    def signedOn(self):
        for channel in self.factory.channels:
            self.join(channel)
    
    # Obviously, called when a PRIVMSG is received. 
    def privmsg(self, user, channel, message):
        nick, _, host = user.partition('!')
        # When channel == self.nickname, the message was sent to the bot 
        # directly and not to a channel. If we're not addressed and this wasn't
        # a direct message, don't do anything.
        if channel != self.nickname and not message.startswith(self.nickname):
            return
        # Strip off any addressing. 
        message = re.sub(
            r'^%s[.,>:;!?]*\s*' % re.escape(self.nickname), '', message)
        command, _, rest = message.partition(' ')
        # Get the function corresponding to the command given. 
        func = getattr(self, 'command_' + command, None)
        # Or, if there was no function, ignore it.
        if func is None:
            return
        # maybeDeferred will always return a Deferred. It calls func(rest), and
        # if that returned a Deferred, return that. Otherwise, return the return
        # value of the function wrapped in twisted.internet.defer.succeed. If
        # an exception was raised, wrap the traceback in 
        # twisted.internet.defer.fail and return that.
        d = defer.maybeDeferred(func, rest)
        # Depending on if this was directly addressed to us or not, change how
        # the response will be sent. If the command succeeded, reply with the
        # result. Otherwise, reply with a terse error message.
        if channel == self.nickname:
            args = [nick]
        else:
            args = [channel, nick]
        d.addCallbacks(self._send_message(*args), self._show_error(*args))
    
    def _send_message(self, target, nick=None):
        def callback(msgs):
            if nick:
                msgs = ['%s: %s' % (nick, msg) for msg in msgs]
            for msg in msgs:
                self.msg(target, msg)
        return callback
    
    def _show_error(self, target, nick=None):
        def errback(f):
            msg = f.getErrorMessage()
            if nick:
                msgs = ['%s: %s' % (nick, msg) for msg in msgs]
            for msg in msgs:
                self.msg(target, msg)
            return f
        return errback
    
    def command_ping(self, rest):
        return ['Pong.']
    
    def command_test(self, rest):
        return ['utf-8 hebrew: \xd7\x98', 'cp1255 hebrew: \xe8', 'utf-8 latin1: \xc3\xa1']
    
    def command_echo(self, rest):
        return ['I see %r' % rest]

class MyFirstIRCFactory(protocol.ReconnectingClientFactory):
    protocol = MyFirstIRCProtocol
    channels = ['#encodingtest', '#xchat', '#python-irc-bots']

if __name__ == '__main__':
    # This runs the program in the foreground. We tell the reactor to connect
    # over TCP using a given factory, and once the reactor is started, it will
    # open that connection.
    reactor.connectTCP(HOST, PORT, MyFirstIRCFactory())
    # Since we're running in the foreground anyway, show what's happening by
    # logging to stdout.
    log.startLogging(sys.stdout)
    # And this starts the reactor running. This call blocks until everything is
    # done, because this runs the whole twisted mainloop.
    reactor.run()

# This runs the program in the background. __name__ is __builtin__ when you use
# twistd -y on a python module.
elif __name__ == '__builtin__':
    # Create a new application to which we can attach our services. twistd wants
    # an application object, which is how it knows what services should be 
    # running. This simplifies startup and shutdown.
    application = service.Application('MyFirstIRCBot')
    # twisted.application.internet.TCPClient is how to make a TCP client service
    # which we can attach to the application.
    ircService = internet.TCPClient(HOST, PORT, MyFirstIRCFactory())
    ircService.setServiceParent(application)
    # twistd -y looks for a global variable in this module named 'application'.
    # Since there is one now, and it's all set up, there's nothing left to do.
