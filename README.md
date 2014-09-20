sedge
------

A configuration manager for OpenSSH ssh\_config(5) files.

Named for the favourite food of the Western Ground Parrot.
If you find this software useful, please consider 
[donating to the effort to save](http://www.givenow.com.au/groundparrot)
this critically endangered species.

Build status
------------

[![Build Status](https://travis-ci.org/grahame/sedge.svg?branch=master)](https://travis-ci.org/grahame/sedge)

Highlights
-----------

 - define classes of hosts, with inheritance
 - per-site definitions describing the hosts in a site. These definitions
can imported by users.
 - easily define hosts which must be accessed through one or more SSH
 tunnels
 - definiton variables (including numeric ranges with optional increments, and 
 sets of valuese)
 - variable expansion within configuration
 - keys can be referenced by fingerprint, and a specific key used for a given host.
   The base directory ~/.ssh is scanned for public/private key pairs, and the
   private key with a matching fingerprint is used. No need to stadardise key 
   file paths & filenames when sharing configuration.
 - allowing programmatic host definitions (eg. compute0, compute1, ..., compute99)

Security notes
--------------

Using @include and shared sedge configuration files requires trust. A malicious 
sedge configuration file can be used to construct an SSH configuration file 
which does harmful things. Only use @include against trusted URLs under your 
control, or under the control of someone you trust.

Example
-------

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

License
-------

Copyright 2014 [Grahame Bowland](mailto:grahame@angrygoats.net).
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
