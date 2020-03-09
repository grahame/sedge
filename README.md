sedge
------

Template and share OpenSSH ssh\_config(5) files. A preprocessor for
OpenSSH configurations.

Named for the favourite food of the Western Ground Parrot.
If you find this software useful, please consider
[donating to the effort to save](http://www.givenow.com.au/groundparrot)
this critically endangered species.

Build status
------------

[![Build Status](https://travis-ci.org/grahame/sedge.svg?branch=master)](https://travis-ci.org/grahame/sedge)

Installation
------------

    pip3 install sedge

Usage
-----
    sedge
    Usage: sedge [OPTIONS] COMMAND [ARGS]...

      Template and share OpenSSH ssh_config(5) files. A preprocessor for OpenSSH
      configurations.

    Options:
      --version                 Show the version and exit.
      -c, --config-file TEXT
      -o, --output-file TEXT
      -n, --no-verify           do not verify HTTPS requests
      -k, --key-directory TEXT  directory to scan for SSH keys
      -v, --verbose
      --help                    Show this message and exit.

    Commands:
      init    Initialise ~./sedge/config file if none...
      keys    Manage ssh keys
      update  Update ssh config from sedge specification



Highlights
-----------

 - Define classes of hosts, with inheritance
 - Per-site definitions describing the hosts in a site. These definitions can imported by users
 - Easily define hosts which must be accessed through one or more SSH tunnels
 - Definition variables (including numeric ranges with optional increments, and sets of values)
 - variable expansion within configuration
 - keys can be referenced by fingerprint, and a specific key used for a given host.
   The base directory ~/.ssh is scanned for public/private key pairs, and the
   private key with a matching fingerprint is used. No need to standardise key
   file paths & file names when sharing configuration.
 - allowing programmatic host definitions (eg. compute0, compute1, ..., compute99)

Security notes
--------------

Using `@include` and shared sedge configuration files requires trust. A malicious
sedge configuration file can be used to construct an SSH configuration file
which does harmful things. Only use `@include` against trusted URLs under your
control, or under the control of someone you trust.

Getting started
---------------

Sedge reads `~/.sedge/config` and uses it to generate `~/.ssh/config`.

Basic usage is simple:

    $ sedge update

No output is generated if all goes well. Use the `-v` flag to get
verbose output, including a diff of any changes made to your `~/.ssh/config`.

Below is an example sedge configuration file. It has the same syntax as an
OpenSSH configuration file, but uses some additional keywords. Sedge
keywords begin with an '@'.

    # global configuration..
    StrictHostKeyChecking no

    # variables we wish to substitute
    @set work-username percival

    # key fingerprints - sedge will find the matching private key
    # useful when keys are shared around, and multiple people are
    # including a sedge config - no need to standardise paths / names
    # for the keys
    @key work-ec2 00:0a:0b:0c:0d:0e:0f:f0:0d:01:02:02:03:04:05:06
    @key work-storage 3e:1a:1b:0c:0d:0e:0f:f0:0d:01:02:02:03:04:05:06
    # OpenSSH 6.8 switched over to SHA256 fingerprints; we can provide both so our
    # sedge configs work on machines with all OpenSSH versions
    @key work-github 8e:1a:3b:0c:0d:0e:0f:f0:0d:01:02:02:03:04:05:06 SHA256:l3mMings9/oSzgKfGWq8uZE4oB+z8lLNNid/Tv51M

    # define a set of host attributes
    @HostAttrs trusted
        ForwardAgent yes

    # ... and another
    @HostAttrs slow-network
        Compression yes
        TCPKeepAlive yes

    Host headnode
        @is slow-network
        @identity work-ec2
        HostName headnode.example.com
        User <work-username>

    # define hosts ceph0, ceph2, .., ceph14
    @with i {0..14/2}
    Host ceph<i>
        @is trusted
        # tunnel through 'headnode'
        @via headnode
        @identity work-storage
        User ceph

    @with i 3 5 8
    Host swift<i>
        @is trusted
        # tunnel through 'headnode'
        @via headnode
        @identity work-storage
        User ceph

    # pull in a public sedge definition; pass this definition an argument
    # in the included file arguments are defined:
    #   @args username
    @include https://example.com/user-nodes.sedge <work-username>

    # ... or we can use a file:///path
    @include file:///path/to/my/file.sedge

    # ... or we can use a path, in which case ~ will be expanded
    @include ~/mystuff/file.sedge

Other functionality
-------------------

Sedge allows you to associate names with your keys. It is helpful to list
the keys you have, and their fingerprints, so you can give them names using
the `@identity`:

    $ sedge list-keys
    SHA256:lkfjFKJdslfjdfdkslFJKLKSjfdkjsdlfkSDJfksjdk  /Users/grahame/.ssh/a-key
    SHA256:ewr12913klajslakjiejrowjeroiwjJJfisjdfjsksd  /Users/grahame/.ssh/another-key

If any of your keys do not have public keys alongside them (eg.
`<mykey>.pub`), sedge will generate the public key file.

Sedge gives you a helpful shortcut to load all of your keys into `ssh-agent`:

    $ sedge add-keys

Keyword documentation
---------------------

`@args [arg ...]` - this keyword defines the names of variables which must
be passed if this file is included from another. Each `arg` will be made
available for substitution.

`@identity <keyname>` - this keyword applies to the current Host stanza.
It requires that only the key `<keyname>` will be offered to log into the
host. This is useful if you are using a host such as github which has a
common user account, and identifies you based on the key offered.

`@include <url> [arg ...]` - include the sedge file at `<url>`. That file
may define one or more arguments with `@arg`, which should be passed
through as arguments to `@include`.

`@is <attr>` - this keyword applies to a Host stanza. All attributes set
within the `@HostAttrs` stanza with name `<attr>` will be applied to the
current host.

`@key <name> <fingerprint>` - this keyword applies globally, and the keys you
define are made available to files included with `@include`. Your `~/.ssh/`
directory will be scanned for keys matching `<fingerprint>`. To find the
fingerprint for your keyfiles, run `sedge list-keys`.

`@set <variable> <val>` - this keyword applies globally within the current
file. The `<variable>` is made available for subsitution within the file.

`@via <host>` - this is a convenience keyword. It expands to a `ProxyCommand`
directive which allows the SSH login to bounce through `<host>`.

`@with <variable> [val ..]` - this keyword applies to the next Host stanza.
The `<variable>` will be made available for subsitution within the stanza,
and the stanza will be repeated for each possible value of `<variable>`.
Values of the format `{a..b}` or `{a..b/c}` are treated specially, and are
expanded to the inclusive range of integers from `a` to `b` with optional
step `c`. If multiple `@with` keywords are applied to a Host stanza, the
product of their values is used for substitution.

License
-------

Copyright 2014-2020 [Grahame Bowland](mailto:grahame@oreamnos.com.au).
See the included file `LICENSE` for copying details.

> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
>
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
> GNU General Public License for more details.
>
> You should have received a copy of the GNU General Public License
> along with this program.  If not, see <http://www.gnu.org/licenses/>.
