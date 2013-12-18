import base64
import binascii

from twisted.conch.checkers import SSHPublicKeyDatabase


class GittoPublicKeyDatabase(SSHPublicKeyDatabase):

    def __init__(self, keyspath):
        self.keyspath = keyspath


    def getAuthorizedKeysFiles(self, credentials):
        return [self.keyspath.child(credentials.username)]


    def checkKey(self, credentials):
        for filepath in self.getAuthorizedKeysFiles(credentials):
            if not filepath.exists():
                continue

            for line in filepath.open():
                l2 = line.split()

                if len(l2) < 2:
                    continue

                try:
                    if base64.decodestring(l2[1]) == credentials.blob:
                        return True
                except binascii.Error:
                    continue

        return False
