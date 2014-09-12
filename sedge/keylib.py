class KeyNotFound(Exception):
    pass


class KeyLibrary:
    def __init__(self):
        self.keys_by_fingerprint = {}

    def scan(self):
        pass

    def lookup(self, fingerprint):
        if fingerprint not in self.keys_by_fingerprint:
            self.scan()
        try:
            return self.keys_by_fingerprint[fingerprint]
        except KeyError:
            raise KeyNotFound()
