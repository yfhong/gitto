from twisted.application import strports
from twisted.cred.portal import Portal
from twisted.python import usage
from twisted.python.filepath import FilePath

from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key

from .checker import GittoPublicKeyDatabase
from .session import GittoRealm


class Options(usage.Options):

    optParameters = [
        ["port",    "p", "tcp:22", "port of ssh server"],
        ["datadir", "d", "data",   "path to data directory"],
        ["key",     "k", "id_rsa", "path to private key of ssh server"]]


def makeService(config):
    key = Key.fromFile(config["key"])
    datapath = FilePath(config['datadir'])

    factory = SSHFactory()
    factory.publicKeys = factory.privateKeys = {key.sshType(): key}

    factory.portal = Portal(
        GittoRealm(datapath),
        [GittoPublicKeyDatabase(datapath.child(".config").child("keys"))])

    return strports.service(config['port'], factory)
