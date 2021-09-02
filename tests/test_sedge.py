import os
import re

import pytest
from io import StringIO

from sedge.engine import SedgeEngine, Host, ConfigOutput
from sedge.urlhandling import get_contents
from sedge.exceptions import (
    ParserException,
    OutputException,
)

from sedge.keylib import KeyLibrary


def config_for_text(in_text):
    library = KeyLibrary("/does-not-exist", verbose=False)
    verify_ssl = True
    return SedgeEngine(library, StringIO(in_text), verify_ssl)


def check_parse_result(in_text, expected_text):
    config = config_for_text(in_text)
    fd = StringIO()
    out = ConfigOutput(fd)
    config.output(out)
    assert expected_text == fd.getvalue()


def test_empty_file():
    check_parse_result("", "")


def test_global_option():
    check_parse_result("GlobalOption\n", "GlobalOption\n")


def test_single_host_stanza():
    check_parse_result("Host blah\n", "Host = blah\n")


def test_expansion():
    check_parse_result(
        """
@with i 1 2
Host percival<i>
""",
        "Host = percival1\n\nHost = percival2\n",
    )


def test_expansion_long_strings():
    check_parse_result(
        """
@with i millet corn
Host percival_<i>
""",
        "Host = percival_millet\n\nHost = percival_corn\n",
    )


def test_combinatoric_expansion():
    check_parse_result(
        """
@with i 1 2
@with j 4 5
Host p<i>-<j>
""",
        "Host = p1-4\n\nHost = p1-5\n\nHost = p2-4\n\nHost = p2-5\n",
    )


def test_simple_is():
    check_parse_result(
        """
@HostAttrs a
    SomeOption Yes
Host blah
    @is a
""",
        "Host = blah\n    SomeOption = Yes\n",
    )


def test_double_is():
    check_parse_result(
        """
@HostAttrs a
    SomeOption Yes
@HostAttrs b
    AnotherOption No
Host blah
    @is a
    @is b
""",
        "Host = blah\n    SomeOption = Yes\n    AnotherOption = No\n",
    )


def test_via():
    check_parse_result(
        """
Host blah
    @via gateway
""",
        "Host = blah\n    ProxyJump = gateway\n",
    )


def test_include_https():
    check_parse_result(
        """
@include https://raw.githubusercontent.com/grahame/sedge/master/ci_data/simple.sedge
""",
        "Host = percival\n    HostName = beaking\n    ForwardAgent = yes\n    ForwardX11 = yes\n",
    )


def test_include_file():
    fpath = os.path.join(os.path.dirname(__file__), "..", "ci_data", "simple.sedge")
    check_parse_result(
        '@include "%s"' % (fpath),
        "Host = percival\n    HostName = beaking\n    ForwardAgent = yes\n    ForwardX11 = yes\n",
    )


def test_include_file_uri():
    fpath = os.path.join(os.path.dirname(__file__), "..", "ci_data", "simple.sedge")
    check_parse_result(
        '@include "file:///%s"' % (fpath),
        "Host = percival\n    HostName = beaking\n    ForwardAgent = yes\n    ForwardX11 = yes\n",
    )


def test_include_strips_root(capsys):
    fpath = os.path.join(
        os.path.dirname(__file__), "..", "ci_data", "strip_global.sedge"
    )
    check_parse_result(
        '@include "%s"' % (fpath),
        "Host = percival\n    HostName = beaking\n    ForwardAgent = yes\n    ForwardX11 = yes\n",
    )
    captured = capsys.readouterr()
    assert captured.err == "\n".join(
        [
            r"Warning: global config in @include 'C:\Work\DevOpsLocal\sedge\tests\..\ci_data\strip_global.sedge' ignored.",
            "Ignored lines are:",
            " > DoesThisGetStripped = hopefully",
            "",
        ]
    )


def test_include_args():
    fpath = os.path.join(os.path.dirname(__file__), "..", "ci_data", "args.sedge")
    check_parse_result(
        """
@set budgerigar percival
@include "%s" <budgerigar>"""
        % fpath,
        "Host = percival\n    HostName = beaking\n",
    )


def test_include_args_not_set():
    fpath = os.path.join(os.path.dirname(__file__), "..", "ci_data", "args.sedge")
    with pytest.raises(
        ParserException,
        match="expected a value for variable '<budgerigar>', set it using @set or @args",
    ) as _:
        config_for_text(
            """
    @set budgerigar2 percival
    @include "%s" <budgerigar> <budgerigar2>"""
            % fpath
        )


def test_include_args_not_included():
    fpath = os.path.join(os.path.dirname(__file__), "..", "ci_data", "args.sedge")
    with open(fpath, "rt") as f, pytest.raises(
        ParserException,
        match="expected a value for variable '<budgie>', set it using @set or @args",
    ) as _:
        check_parse_result(f.read(), "Host = <budgie>\n    HostName = beaking\n")


def test_include_args_not_set_not_passed():
    fpath = os.path.join(os.path.dirname(__file__), "..", "ci_data", "args.sedge")
    with pytest.raises(
        ParserException, match="required arguments not passed to include"
    ) as _:
        config_for_text('@include "%s"' % fpath)


def check_fingerprint(data, fingerprint):
    determined = KeyLibrary._fingerprint_from_keyinfo(data)
    assert determined == fingerprint


def test_fingerprint_parser():
    check_fingerprint(
        "2048 aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38 grahame@anglachel (RSA)",
        "aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38",
    )


def test_fingerprint_parser_double_space():
    check_fingerprint(
        "2048 aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38  grahame@anglachel (RSA)",
        "aa:cb:d2:e2:00:6f:21:b4:fe:39:92:ed:eb:5e:4d:38",
    )


def test_fingerprint_parser_no_comment():
    check_fingerprint(
        "2048 SHA256:gUGtJb8Rh0tHHVwTg6chw7LIis7Vx7KBxCBjU1HYehk no comment (RSA)",
        "SHA256:gUGtJb8Rh0tHHVwTg6chw7LIis7Vx7KBxCBjU1HYehk",
    )


def test_fingerprint_parser_windows():
    check_fingerprint(
        "256 SHA256:aaaaaaaauooSjmHO/YZwHbc/jLIGPryiV7BTbbbbYIw david brent@DESKTOP-PC (ED25519)\r\n",
        "SHA256:aaaaaaaauooSjmHO/YZwHbc/jLIGPryiV7BTbbbbYIw",
    )


def check_config_parser(s, expected):
    result = SedgeEngine.parse_config_line(s)
    assert result == expected


def test_parser_noarg():
    check_config_parser("Keyword", ("Keyword", []))


def test_parser_noarg_trailingspc():
    check_config_parser("Keyword ", ("Keyword", []))


def test_parser_noarg_leadingspc():
    check_config_parser(" Keyword", ("Keyword", []))


def test_parser_onearg():
    check_config_parser("Keyword Arg1", ("Keyword", ["Arg1"]))


def test_parser_onearg_dblspc():
    check_config_parser("Keyword  Arg1", ("Keyword", ["Arg1"]))


def test_parser_twoargs():
    check_config_parser("Keyword Arg1 Arg2", ("Keyword", ["Arg1", "Arg2"]))


def test_parser_twoargs_dblspc():
    check_config_parser("Keyword  Arg1  Arg2", ("Keyword", ["Arg1", "Arg2"]))


def test_parser_quotearg_nospc():
    check_config_parser('Keyword "Arg1"', ("Keyword", ["Arg1"]))


def test_parser_quotearg_withspc():
    check_config_parser('Keyword "Arg1 NotArg2"', ("Keyword", ["Arg1 NotArg2"]))


def test_parser_quotearg_withspc_and_leading():
    check_config_parser('Keyword  "Arg1 NotArg2"', ("Keyword", ["Arg1 NotArg2"]))


def test_parser_quotearg_withspc_and_trailing():
    check_config_parser('Keyword "Arg1 NotArg2" ', ("Keyword", ["Arg1 NotArg2"]))


def test_parser_quotearg_withspc_and_leadin_and_trailing():
    check_config_parser('Keyword  "Arg1 NotArg2" ', ("Keyword", ["Arg1 NotArg2"]))


def test_parser_quotearg_noquotearg():
    check_config_parser(
        'Keyword "Arg1 NotArg2" Arg2', ("Keyword", ["Arg1 NotArg2", "Arg2"])
    )


def test_parser_noquotearg_quotearg():
    check_config_parser(
        'Keyword Arg1 "Arg2 NotArg3"', ("Keyword", ["Arg1", "Arg2 NotArg3"])
    )


def test_parser_quotearg_noquotearg_quotearg():
    check_config_parser(
        'Keyword "Arg1 NotArg2" Arg2', ("Keyword", ["Arg1 NotArg2", "Arg2"])
    )


def test_parser_quotearg_invalid_quote():
    with pytest.raises(ParserException, match="unterminated quotation marks") as _:
        check_config_parser('Keyword "Arg1 NotArg2 Arg2', ("fails"))


def test_parser_quotearg_too_many_quotes():
    with pytest.raises(
        ParserException, match="quotation marks cannot be used within an argument value"
    ) as _:
        check_config_parser('Keyword "Arg1 Not"Arg2" Arg2', ("fails"))


def test_parser_equals_nospc():
    check_config_parser("Keyword=Value", ("Keyword", ["Value"]))


def test_parser_equals_leftspc():
    check_config_parser("Keyword =Value", ("Keyword", ["Value"]))


def test_parser_equals_rightspc():
    check_config_parser("Keyword= Value", ("Keyword", ["Value"]))


def test_parser_equals_bothspc():
    check_config_parser("Keyword = Value", ("Keyword", ["Value"]))


def test_parser_equals_allthespc():
    check_config_parser("Keyword   =   Value", ("Keyword", ["Value"]))


def check_to_line(keyword, parts, expected, **kwargs):
    result = ConfigOutput.to_line(keyword, parts, **kwargs)
    assert result == expected


def test_to_line_no_args():
    check_to_line("Test", [], "Test")


def test_to_line_one_arg():
    check_to_line("Test", ["Hello"], "Test = Hello")


def test_to_line_one_arg_with_quotes():
    check_to_line("Test", ['Hello "fun fun'], 'Test = Hello "fun fun')


def test_to_line_two_args():
    check_to_line("Test", ["Arg1", "Arg2"], "Test Arg1 Arg2")


def test_to_line_two_args_spaces():
    check_to_line(
        "Test",
        ["Arg1 is Spacey", "Arg2 is also Spacey"],
        "Test Arg1 is Spacey Arg2 is also Spacey",
    )


def test_to_line_two_args_spaces_quotes():
    with pytest.raises(OutputException) as _:
        ConfigOutput.to_line("Test", ['This has a quote"', "Eep"])


def test_root_is_fails():
    with pytest.raises(ParserException) as _:
        config_for_text("@is a-thing")


def test_invalid_range_fails():
    with pytest.raises(ParserException) as _:
        Host.expand_with(["{1}"])


def test_invalid_range_dup_fails():
    with pytest.raises(ParserException) as _:
        Host.expand_with(["{1..2..4}"])


def test_invalid_padded_range_dup_fails():
    with pytest.raises(ParserException) as _:
        Host.expand_with(["{001..002..004}"])


def test_invalid_range_nonint_fails():
    with pytest.raises(ParserException) as _:
        Host.expand_with(["{1..cat}"])


def test_invalid_padded_range_nonint_fails():
    with pytest.raises(ParserException) as _:
        Host.expand_with(["{001..cat}"])


def test_invalid_range_empty():
    with pytest.raises(ParserException) as _:
        Host.expand_with(["{}"])


def test_expand():
    assert ["1", "2", "3"] == Host.expand_with(["{1..3}"])


def test_padded_expand():
    assert ["001", "002", "003"] == Host.expand_with(["{001..003}"])


def test_expand_range():
    assert ["1", "3"] == Host.expand_with(["{1..3/2}"])


def test_padded_expand_range():
    assert ["001", "003"] == Host.expand_with(["{001..003/2}"])


def test_padded_expand_range_diff_width():
    assert ["1", "3"] == Host.expand_with(["{01..003/2}"])


def test_http_disallowed():
    with pytest.raises((FileNotFoundError, OSError)) as _:
        get_contents("http://example.com/thing.sedge", True)


def test_subst():
    check_parse_result(
        "@set goat cheese\n@set username percy\nHost <goat>\nUsername <username>",
        "Host = cheese\n    Username = percy\n",
    )


def test_subst_with_via():
    check_parse_result(
        "@set goat cheese\n\nHost test\n@via <goat>",
        "Host = test\n    ProxyJump = cheese\n",
    )


def test_duplicate_host(capsys):
    check_parse_result(
        "Host duplicated\nHostName duplicate1\nHost duplicated\nHostName duplicate2",
        "Host = duplicated\n    HostName = duplicate1\n\nHost = duplicated\n    HostName = duplicate2\n",
    )
    captured = capsys.readouterr()
    assert captured.err == "Warning: duplicated hosts parsing 'None'\n  duplicated\n"


def test_unknown_keyword():
    with pytest.raises(ParserException, match="unknown expansion keyword @blah") as _:
        check_parse_result("@blah hello", "fails")


def test_duplicate_section():
    with pytest.raises(
        ParserException, match="More than one section with name 'trusted'"
    ) as _:
        check_parse_result(
            "@HostAttrs trusted\n    ForwardAgent yes \n@HostAttrs trusted\n    ForwardAgent yes\n Host cheese\n @is trusted",
            "fails",
        )


def test_missing_section():
    with pytest.raises(ParserException, match="No such section: trusted") as _:
        check_parse_result("Host cheese\n @is trusted", "fails")


def test_invalid_key_def():
    with pytest.raises(
        ParserException, match=re.escape("usage: @key <name> [fingerprint]...")
    ) as _:
        check_parse_result("@key blah", "fails")


def test_missing_key_def(capsys):
    check_parse_result("Host mycheese\n@identity blah", "Host = mycheese\n")
    captured = capsys.readouterr()
    assert (
        captured.err
        == "None: identity 'blah' is not defined (missing @key definition)\n"
    )


def test_key_def(capsys):
    check_parse_result(
        "@key mykey 00:0a:0b:0c:0d:0e:0f:f0:0d:01:02:02:03:04:05:06\n Host goatcheese\n @identity mykey",
        "Host = goatcheese\n",
    )
    captured = capsys.readouterr()
    assert (
        captured.err
        == "None: identity 'mykey' (fingerprints 00:0a:0b:0c:0d:0e:0f:f0:0d:01:02:02:03:04:05:06) "
        "not found in SSH key library\n"
    )
