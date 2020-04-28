import os
import re
import urllib.request
import urllib.parse
import requests
from .exceptions import SecurityException

is_https = re.compile(r"^https:")
is_file = re.compile(r"^file:")


def get_contents(target, verify_ssl):
    """
    read the contents of target, which might be a https or file URL,
    or just a local path
    """

    def assert_scheme(url, scheme):
        assert urllib.parse.urlparse(url).scheme == scheme

    # use of a regular expression here is slightly naff, but it's
    # harmless and we are extremely limited in the URLs we will open,
    # and we double-check the scheme with urllib
    if is_https.match(target):
        assert_scheme(target, "https")
        res = requests.get(target, verify=verify_ssl)
        if res.status_code != 200:
            raise SecurityException(
                "HTTP status {}: refusing to use contents of {}".format(
                    res.status_code, target
                )
            )
        return res.text

    if is_file.match(target):
        assert_scheme(target, "file")
        return urllib.request.urlopen(target).read().decode("utf8")

    with open(os.path.expanduser(target)) as fd:
        return fd.read()
