import os
import os.path
import shlex
import sys

from twisted.cred.portal import IRealm
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.python import components

from twisted.conch.avatar import ConchUser
from twisted.conch.ssh.session import ISession, wrapProtocol, SSHSession

from zope.interface import implements



class DeafProtocol(Protocol):

    def __init__(self, datapath):
        self.datapath = datapath


    def connectionMade(self):
        banner = self.datapath.child('.config').child('BANNER')

        if banner.exists():
            with banner.open() as f:
                self.transport.write(f.read().replace('\n', '\r\n'))

        self.transport.loseConnection()



class DummyTransport:

    def loseConnection(self):
        pass



class GittoSession:
    implements(ISession)

    def __init__(self, avatar):
        self.avatar = avatar
        self.pty = None


    def getPty(self, term, windowSize, attrs):
        pass


    def closed(self):
        pass


    def eofReceived(self):
        if self.pty:
            self.pty.closeStdin()


    def _die(self, proto, message):
        proto.makeConnection(DummyTransport())
        proto.errReceived(message)
        proto.loseConnection()


    def _fail(self, fail, proto):
        self._die(proto, "ERROR: internal server error\n")


    def execCommand(self, proto, cmd):
        argv = shlex.split(cmd)
        environ = os.environ.copy()
        environ["GITTO_USER"] = self.avatar.username
        environ["GITTO_DATADIR"] = self.avatar.datapath.path

        self.pty = reactor.spawnProcess(
            proto,
            sys.executable,
            ['python', '-m', 'gitto.client'] + argv,
            env=environ)


    def openShell(self, trans):
        ep = DeafProtocol(self.avatar.datapath)
        ep.makeConnection(trans)
        trans.makeConnection(wrapProtocol(ep))



class GittoUser(ConchUser):

    def __init__(self, username, datapath):
        ConchUser.__init__(self)
        self.username = username
        self.datapath = datapath
        self.channelLookup["session"] = SSHSession


    def logout(self):
        pass


components.registerAdapter(GittoSession, GittoUser, ISession)


class GittoRealm:
    implements(IRealm)

    def __init__(self, datapath):
        self.datapath = datapath

    def requestAvatar(self, username, mind, *interfaces):
        user = GittoUser(username, self.datapath)
        return interfaces[0], user, user.logout
