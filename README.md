sedge
------

A configuration manager for OpenSSH ssh\_config(5) files.

Named for the favourite food of the Western Ground Parrot.
If you find this software useful, please consider 
[donating to the effort to save](http://www.givenow.com.au/groundparrot)
this critically endangered species.

Highlights
-----------

 - define classes of hosts, with inheritance
 - per-site definitions describing the hosts in a site. These definitions
can imported by users.
 - easily define hosts which must be accessed through one or more SSH
 tunnels
 - define variables (including numeric ranges with optional increments, and 
 sets of valuese)
 - variable expansion within configuration
 - allowing programmatic host definitions (eg. compute0, compute1, ..., compute99)

Example
-------

    # global configuration..
    StrictHostKeyChecking no

    # define a set of host attributes
    @HostAttrs trusted
        ForwardAgent yes
        ForwardX11 yes

    # ... and another
    @HostAttrs slow-network
        Compression yes
        TCPKeepAlive yes

    Host headnode
        @is slow-network
        HostName headnode.example.com
        User work-username

    # define hosts ceph0, ceph2, .., ceph14
    @with i {0..14/2}
    Host ceph<i>
        @is trusted
        # tunnel through 'headnode'
        @via headnode
        User ceph
        IdentifyFile ~/.ssh/ceph-id.rsa

    @with i 3 5 8
    Host swift<i>
        @is trusted
        # tunnel through 'headnode'
        @via headnode
        User ceph
        IdentifyFile ~/.ssh/ceph-id.rsa

    # pull in a public sedge definition
    @include http://example.com/user-nodes.sedge

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
