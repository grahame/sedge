from io import StringIO
from .parser import SedgeConfig
from nose.tools import eq_


def check_parse_result(in_text, out_text):
    config = SedgeConfig(StringIO(in_text))
    outfd = StringIO()
    config.output(outfd)
    eq_(outfd.getvalue(), out_text)


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
