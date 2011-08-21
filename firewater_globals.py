#! /usr/bin/env python
#
#	firewater_globals.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

VERSION = 0.1

DEBUG = False

# dictionary holding interface aliases and groups
INTERFACES = { 'all' : [] }

# dictionary with host and network range aliases
HOSTS = { 'any' : [ '0.0.0.0/0' ],
	'everybody' : [ '0.0.0.0/0' ] }

# dictionary with user-defined ServiceObjects
SERVICES = {}

# the chain that rules have effect on right now
CURRENT_CHAIN = 'incoming'

# static list of known protocols
KNOWN_PROTOCOLS = ('tcp', 'udp', 'ip', 'icmp', 'gre')

# EOB
