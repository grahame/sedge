import os
import subprocess
import sys


class KeyNotFound(Exception):
    pass


class FingerprintDoesNotParse(Exception):
    pass


class KeyLibrary:
    def __init__(self, path, verbose=False):

        self._path = path
        self._verbose = verbose
        self.keys_by_fingerprint = {}
        self._scan()

    def _generate_public_key(self, fname):
        pkey_fname = fname + '.pub'
        if os.access(pkey_fname, os.R_OK):
            return
        print("public key does not exist for private key '{name}'".format(name=fname), file=sys.stderr)
        print("attempting to generate; you may be prompted for a pass phrase.", file=sys.stderr)
        try:
            public_key = subprocess.check_output(['ssh-keygen', '-y', '-f', fname])
        except subprocess.CalledProcessError:
            return
        with open(pkey_fname, 'wb') as fd:
            fd.write(public_key)
        print("Generated public key successfully.", file=sys.stderr)
        return True

    @classmethod
    def _fingerprint_from_keyinfo(cls, output):
        parts = [s for s in (t.strip() for t in output.split(' ')) if s]
        if len(parts) != 4:
            raise FingerprintDoesNotParse()
        return parts[1]

    def _scan_key(self, fname, recurse=False):
        try:
            output = subprocess.check_output(['ssh-keygen', '-l', '-f', fname]).decode('utf8')
            try:
                return KeyLibrary._fingerprint_from_keyinfo(output)
            except FingerprintDoesNotParse:
                print("warning: public key fingerprint couldn't be parsed: '%s'" % fname, file=sys.stderr)
                print(output, file=sys.stderr)
        except subprocess.CalledProcessError:
            if not recurse and self._generate_public_key(fname):
                return self._scan_key(fname, recurse=True)

    def _scan(self):
        def rp(path):
            return os.path.relpath(path, self._path)

        skip = {'config', 'known_hosts', 'known_hosts.old', 'authorized_keys'}
        for dirpath, dirnames, fnames in os.walk(self._path):
            for name, path in ((t, os.path.join(dirpath, t)) for t in fnames):
                if name.startswith('.'):
                    continue
                if name.endswith('.pub'):
                    continue
                if name in skip:
                    continue
                fingerprint = self._scan_key(path)
                if fingerprint is not None:
                    if self._verbose:
                        print("scanned key '{key}' fingerprint '{fingerprint}'".format(
                            key=rp(path),
                            fingerprint=fingerprint)
                        )
                    if fingerprint in self.keys_by_fingerprint:
                        print(
                            "warning: key '{key}' has same fingerprint as '{otherkey}', ignoring duplicate key.".format(
                                key=rp(self.keys_by_fingerprint[fingerprint]),
                                otherkey=rp(path))
                        )
                    else:
                        self.keys_by_fingerprint[fingerprint] = path

    def list_keys(self):
        max_finger = max(len(t) for t in self.keys_by_fingerprint)
        for k, v in sorted(self.keys_by_fingerprint.items(), key=lambda x: x[1]):
            print("%*s  %s" % (max_finger, k, v))

    def add_keys(self):
        files = list(sorted(set(self.keys_by_fingerprint.values())))
        subprocess.call(['ssh-add'] + files)

    def lookup(self, fingerprint):
        try:
            return self.keys_by_fingerprint[fingerprint]
        except KeyError:
            raise KeyNotFound()
