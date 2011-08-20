#! /usr/bin/env python
#
#	firewater_service.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#


class ServiceObject:
	'''object respresenting a service'''
	
	def __init__(self, name=None, port=0, endport=0, proto=None, iface=None):
		self.name = name
		self.proto = proto			# forced protocol
		self.port = port
		self.endport = endport		# it can be a port range
		self.iface = iface			# forced onto an interface
	
	def __str__(self):
		return '<ServiceObject: %s,%s,%d,%d,%s>' % (self.name, self.proto, self.port, self.endport, self.iface)

# EOB

