from click.testing import CliRunner

from sedge.cli import cli, init, update, keys


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert (
        result.output.replace("\n", "")
        == """Usage: cli [OPTIONS] COMMAND [ARGS]...
  Template and share OpenSSH ssh_config(5) files. A preprocessor for OpenSSH  configurations.
Options:
  --version                 Show the version and exit.
  -c, --config-file TEXT
  -o, --output-file TEXT
  -n, --no-verify           do not verify HTTPS requests
  -k, --key-directory TEXT  directory to scan for SSH keys
  -v, --verbose
  --help                    Show this message and exit.
Commands:
  init    Initialise ~./sedge/config file if none exists.
  keys    Manage ssh keys
  update  Update ssh config from sedge specification
""".replace(
            "\n", ""
        )
    )


def test_init_help():
    runner = CliRunner()
    result = runner.invoke(init, ["--help"])
    assert result.exit_code == 0
    assert (
        result.output
        == """Usage: init [OPTIONS]

  Initialise ~./sedge/config file if none exists. Good for first time sedge
  usage

Options:
  --help  Show this message and exit.
"""
    )


def test_update_help():
    runner = CliRunner()
    result = runner.invoke(update, ["--help"])
    assert result.exit_code == 0
    assert (
        result.output
        == """Usage: update [OPTIONS]

  Update ssh config from sedge specification

Options:
  --help  Show this message and exit.
"""
    )


def test_keys_help():
    runner = CliRunner()
    result = runner.invoke(keys, ["--help"])
    assert result.exit_code == 0
    assert (
        result.output
        == """Usage: keys [OPTIONS] COMMAND [ARGS]...

  Manage ssh keys

Options:
  --help  Show this message and exit.

Commands:
  add
  list
"""
    )
