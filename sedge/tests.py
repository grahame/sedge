from io import StringIO
from .parser import SedgeConfig
from .keylib import KeyLibrary
from nose.tools import eq_


def check_parse_result(in_text, out_text):
    library = KeyLibrary('/tmp')
    config = SedgeConfig(library, StringIO(in_text))
    outfd = StringIO()
    config.output(outfd)
    eq_(out_text, outfd.getvalue())


def test_empty_file():
    check_parse_result('', '\n')


def test_global_option():
    check_parse_result('GlobalOption\n', 'GlobalOption\n')


def test_single_host_stanza():
    check_parse_result('Host blah\n', '\nHost blah\n\n')


def test_expansion():
    check_parse_result('''
@with i 1 2
Host percival<i>
''', '\nHost percival1\n\nHost percival2\n\n')


def test_combinatoric_expansion():
    check_parse_result('''
@with i 1 2
@with j 4 5
Host p<i>-<j>
''', '\nHost p1-4\n\nHost p1-5\n\nHost p2-4\n\nHost p2-5\n\n')


def test_simple_is():
    check_parse_result('''
@HostAttrs a
    SomeOption Yes
Host blah
    @is a
''', '\nHost blah\n    SomeOption Yes\n\n')


def test_double_is():
    check_parse_result('''
@HostAttrs a
    SomeOption Yes
@HostAttrs b
    AnotherOption No
Host blah
    @is a
    @is b
''', '\nHost blah\n    SomeOption Yes\n    AnotherOption No\n\n')


def test_via():
    check_parse_result('''
Host blah
    @via gateway
''', '\nHost blah\n    ProxyCommand ssh gateway nc %h %p 2> /dev/null\n\n')


def test_include():
    check_parse_result('''
@include https://raw.githubusercontent.com/grahame/sedge/master/ci_data/simple.sedge
''', '\nHost percival\n    HostName beaking\n    ForwardAgent yes\n    ForwardX11 yes\n\n')


def test_include_strips_root():
    check_parse_result('''
@include https://raw.githubusercontent.com/grahame/sedge/master/ci_data/strip_global.sedge
''', '\nHost percival\n    HostName beaking\n    ForwardAgent yes\n    ForwardX11 yes\n\n')


def check_fingerprint(data, fingerprint):
    determined = KeyLibrary._fingerprint_from_keyinfo(data)
    eq_(determined, fingerprint)


def test_fingerprint_parser():
    check_fingerprint(
        '2048 aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38 grahame@anglachel (RSA)',
        'aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38')


def test_fingerprint_parser_double_space():
    check_fingerprint(
        '2048 aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38  grahame@anglachel (RSA)',
        'aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38')
