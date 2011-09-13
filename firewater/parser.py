#
#	firewater/parser.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2003-2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

#
#	To make a new keyword for the input file, simply define a
#	function here like: def parse_xxx(arr, filename, lineno, line):
#	and it will just work (magic trick with getattr(module, functionname))
#

import firewater.globals
import firewater.resolv
import firewater.service
import firewater.bytecode

from firewater.lib import *

import os
import sys
import string


# status; are we copying verbatim or not?
IN_VERBATIM = False

# nested ifdefs
IFDEF_LEVEL = 0


class ParseError(Exception):
	'''error message class for parse errors'''
	
	def __init__(self, msg):
		Exception.__init__(self)
		self.msg = msg
	
	def __repr__(self):
		return self.msg
	
	def __str__(self):
		return self.msg
	
	def perror(self):
		stderr(self.msg)


def read_input_file(filename):	# throws IOError
	'''read a (included) input file
	Returns 0 on success, or error count on errors'''

	saved_ifdef_level = IFDEF_LEVEL
	
	f = open(filename, 'r')
	
	this_module = sys.modules['firewater.parser']
	
	lineno = 0
	errors = 0
	
	#
	#	read lines from the input file
	#	variable tmp_line is used to be able to do multi-line reads (backslash terminated)
	#
	line = ''
	while True:
		tmp_line = f.readline()
		if not tmp_line:
			break
		
		lineno = lineno + 1
		
		if IN_VERBATIM:
			# copy verbatim until the statement 'end verbatim' is reached
			verbatim_line = string.strip(tmp_line)
			arr = string.split(string.lower(verbatim_line))
			# it is tested with an array so that both spaces and tabs work
			# note that this shadows the 'end' keyword, but only when in verbatim mode
			if not (len(arr) == 2 and arr[0] == 'end' and arr[1] == 'verbatim'):
				debug('verbatim line == [%s]' % verbatim_line)
				firewater.globals.VERBATIM.append(verbatim_line)
				continue
		
		n = string.find(tmp_line, '#')
		if n >= 0:
			stripped_comment = '    ' + string.strip(tmp_line[n:])
			tmp_line = tmp_line[:n]		# strip comment
		else:
			stripped_comment = ''
		
		tmp_line = string.strip(tmp_line)
		if not tmp_line:
			continue
		
		if tmp_line[-1] == '\\':
			tmp_line = string.strip(tmp_line[:-1])
			line = line + ' ' + tmp_line
			continue
		
		line = line + ' ' + tmp_line
		tmp_line = ''
		
		arr = string.split(line)
		
		# insert the line into bytecode as comment
		# (this will be displayed in verbose mode)
		bytecode = firewater.bytecode.ByteCode()
		bytecode.set_comment(filename, lineno, line + stripped_comment)
		firewater.globals.BYTECODE.append(bytecode)
		
		line = ''	# <-- line is being reset here; use arr[] from here on
		
		keyword = string.lower(arr[0])
		
		# get the parser function
		try:
			func = getattr(this_module, 'parse_%s' % keyword)
		except AttributeError:
			stderr("%s:%d: unknown keyword '%s'" % (filename, lineno, keyword))
			errors = errors + 1
			continue
		
		try:
			func(arr, filename, lineno)
		except ParseError, (parse_error):
			parse_error.perror()
			errors = errors + 1
	
	f.close()
	
	if IN_VERBATIM:
		ParseError("%s:%d: missing 'end verbatim' statement" % (filename, lineno)).perror()
		errors = errors + 1
	
	if IFDEF_LEVEL > saved_ifdef_level:
		ParseError("%s:%d: missing 'endif' statement" % (filename, lineno)).perror()
		errors = errors + 1
	
	elif IFDEF_LEVEL < saved_ifdef_level:
		ParseError("%s:%d: too many 'endif' statements" % (filename, lineno)).perror()
		errors = errors + 1
	
	debug('errors == %d' % errors)
	return errors


def _is_ipv4_address(addr):
	'''returns True if addr looks like an IPv4 address'''
	'''or False if not'''

	arr = string.split(addr, '.')
	if not arr:
		return False
	
	if len(arr) != 4:
		return False
	
	for i in xrange(0, 4):
		try:
			n = int(arr[i])
		except ValueError:
			return False

		if n < 0 or n > 255:
			return False
	
	return True


# keyword: include
def parse_include(arr, filename, lineno):
	if len(arr) <= 1:
		raise ParseError("%s:%d: 'include' requires a filename argument" % (filename, lineno))
	
	include_file = string.join(arr[1:])
	
	debug('include %s' % include_file)
	
	try:
		# recursively read the given parse file
		if read_input_file(include_file) > 0:
			raise ParseError("%s:%d: error in included file %s" % (filename, lineno, include_file))
	
	except IOError:
		raise ParseError("%s:%d: failed to read file '%s'" % (filename, lineno, include_file))


def parse_iface(arr, filename, lineno):
	parse_interface(arr, filename, lineno)


def parse_interface(arr, filename, lineno):
	if len(arr) < 3:
		raise ParseError("%s:%d: '%s' requires at least 2 arguments: the interface alias and the real interface name" % (filename, lineno, arr[0]))
	
	alias = arr[1]
	if alias == 'any':
		raise ParseError("%s:%d: 'any' is a reserved word" % (filename, lineno))
	
	iface_list = string.join(arr[2:])
	iface_list = string.split(iface_list, ',')
	
	if alias in iface_list:
		raise ParseError("%s:%d: interface %s references back to itself" % (filename, lineno, alias))
	
	if firewater.globals.INTERFACES.has_key(alias):
		raise ParseError("%s:%d: redefinition of interface %s" % (filename, lineno, alias))
	
	# expand the list by filling in any previously defined aliases
	new_iface_list = []
	while len(iface_list) > 0:
		iface = iface_list.pop(0)
		if firewater.globals.INTERFACES.has_key(iface):
			iface_list.extend(firewater.globals.INTERFACES[iface])
		else:
			# treat as real system interface name
			if not iface in new_iface_list:
				new_iface_list.append(iface)
	
	debug('new interface: %s:%s' % (alias, new_iface_list))
	
	firewater.globals.INTERFACES[alias] = new_iface_list
	
	all_ifaces = firewater.globals.INTERFACES['all']
	for iface in new_iface_list:
		if not iface in all_ifaces:
			all_ifaces.append(iface)


def parse_debug(arr, filename, lineno):
	if len(arr) < 2:
		raise ParseError("%s:%d: usage: debug interfaces|hosts|services" % (filename, lineno))
	
	if arr[1] in ('iface', 'interfaces'):
		print 'firewater.globals.INTERFACES ==', firewater.globals.INTERFACES
		print
		return
	
	if arr[1] in ('host', 'hosts'):
		print 'firewater.globals.HOSTS ==', firewater.globals.HOSTS
		print
		return
	
	if arr[1] in ('services', 'serv'):
		print 'firewater.globals.SERVICES ==', firewater.globals.SERVICES
		print
		return
	
	raise ParseError("%s:%d: don't know how to debug '%s'" % (filename, lineno, arr[1]))


def parse_host(arr, filename, lineno):
	if len(arr) < 3:
		raise ParseError("%s:%d: 'host' requires at least 2 arguments: the host alias and the IP address or fqdn" % (filename, lineno))
	
	alias = arr[1]
	if alias == 'any':
		raise ParseError("%s:%d: 'any' is a reserved word" % (filename, lineno))
	
	host_list = string.join(arr[2:])
	host_list = string.replace(host_list, ' ', '')
	host_list = string.replace(host_list, ',,', ',')
	host_list = string.split(host_list, ',')
	
	if alias in host_list:
		raise ParseError("%s:%d: host %s references back to itself" % (filename, lineno, alias))
	
	if firewater.globals.HOSTS.has_key(alias):
		raise ParseError("%s:%d: redefinition of host %s" % (filename, lineno, alias))
	
	# expand the list by filling in any previously defined aliases
	new_host_list = []
	while len(host_list) > 0:
		host = host_list.pop(0)
		if firewater.globals.HOSTS.has_key(host):
			host_list.extend(firewater.globals.HOSTS[host])
		else:
			# treat as IP address or fqdn
			if string.find(host, ':') > -1:
				# treat as IPv6 address
				pass
			
			elif string.find(host, '/') > -1:
				# treat as network range
				a = string.split(host, '/')
				if len(a) != 2:
					raise ParseError("%s:%d: invalid host address '%s'" % (filename, lineno, host))
				
				if not _is_ipv4_address(a[0]):
					raise ParseError("%s:%d: invalid host address '%s'" % (filename, lineno, host))
				
				if a[1] != '32':
					raise ParseError("%s:%d: invalid host address '%s'" % (filename, lineno, host))
				
				pass
			
			elif _is_ipv4_address(host):
				# treat as IPv4 address
				pass
			
			else:
				# treat as fqdn, so resolve the address
				addrs = firewater.resolv.resolv(host)
				if addrs == None:	# error
					raise ParseError("%s:%d: failed to resolve '%s'" % (filename, lineno, host))
				
				for addr in addrs:
					if not addr in new_host_list:
						new_host_list.append(addr)
				
				continue
			
			if not host in new_host_list:
				new_host_list.append(host)
	
	debug('new host: %s:%s' % (alias, new_host_list))
	
	firewater.globals.HOSTS[alias] = new_host_list


def parse_range(arr, filename, lineno):
	if len(arr) < 3:
		raise ParseError("%s:%d: 'range' requires at least 2 arguments: the range alias and the address range" % (filename, lineno))
	
	alias = arr[1]
	if alias == 'any':
		raise ParseError("%s:%d: 'any' is a reserved word" % (filename, lineno))
	
	ranges_list = string.join(arr[2:])
	ranges_list = string.replace(ranges_list, ' ', '')
	ranges_list = string.replace(ranges_list, ',,', ',')
	ranges_list = string.split(ranges_list, ',')
	
	if alias in ranges_list:
		raise ParseError("%s:%d: range %s references back to itself" % (filename, lineno, alias))
	
	# note that ranges are stored in the same way as hosts
	if firewater.globals.HOSTS.has_key(alias):
		raise ParseError("%s:%d: redefinition of range or host %s" % (filename, lineno, alias))
	
	# expand the list by filling in any previously defined aliases
	new_ranges_list = []
	while len(ranges_list) > 0:
		# 'range' is a Python keyword ... so I use 'host' instead (confusing huh?)
		host = ranges_list.pop(0)
		if firewater.globals.HOSTS.has_key(host):
			ranges_list.extend(firewater.globals.HOSTS[host])
		else:
			# treat as IP address or fqdn
			if string.find(host, ':') > -1:
				# treat as IPv6 address
				pass
			
			elif string.find(host, '/') > -1:
				# treat as network range
				a = string.split(host, '/')
				if len(a) != 2:
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, host))
				
				if not _is_ipv4_address(a[0]):
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, host))
				
				try:
					bits = int(a[1])
				except ValueError:
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, host))
				
				if bits < 0 or bits > 32:
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, host))
			
			else:
				raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, host))
			
			if not host in new_ranges_list:
				new_ranges_list.append(host)
	
	debug('new range: %s:%s' % (alias, new_ranges_list))
	
	firewater.globals.HOSTS[alias] = new_ranges_list


def parse_group(arr, filename, lineno):
	if len(arr) < 3:
		raise ParseError("%s:%d: 'group' requires at least 2 arguments: the group alias and at least 1 member" % (filename, lineno))
	
	alias = arr[1]
	if alias == 'any':
		raise ParseError("%s:%d: 'any' is a reserved word" % (filename, lineno))
	
	group_list = string.join(arr[2:], ',')
	group_list = string.replace(group_list, ' ', '')
	group_list = string.replace(group_list, ',,', ',')
	group_list = string.split(group_list, ',')
	
	if alias in group_list:
		raise ParseError("%s:%d: range %s references back to itself" % (filename, lineno, alias))
	
	# note that group are stored in the same way as groups
	if firewater.globals.HOSTS.has_key(alias):
		raise ParseError("%s:%d: redefinition of range or group %s" % (filename, lineno, alias))
	
	# expand the list by filling in any previously defined aliases
	new_group_list = []
	while len(group_list) > 0:
		group = group_list.pop(0)
		if firewater.globals.HOSTS.has_key(group):
			group_list.extend(firewater.globals.HOSTS[group])
		else:
			# treat as IP address or fqdn
			if string.find(group, ':') > -1:
				# treat as IPv6 address
				pass
			
			elif string.find(group, '/') > -1:
				# treat as network range
				a = string.split(group, '/')
				if len(a) != 2:
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, group))
				
				if not _is_ipv4_address(a[0]):
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, group))
				
				try:
					bits = int(a[1])
				except ValueError:
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, group))
				
				if bits < 0 or bits > 32:
					raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, group))
			
			else:
				# treat as fqdn, so resolve the address
				addrs = firewater.resolv.resolv(group)
				if addrs == None:	# error
					raise ParseError("%s:%d: failed to resolve '%s'" % (filename, lineno, group))
				
				for addr in addrs:
					if not addr in new_group_list:
						new_group_list.append(addr)
				
				continue
			
			if not group in new_group_list:
				new_group_list.append(group)
	
	debug('new group: %s:%s' % (alias, new_group_list))
	
	firewater.globals.HOSTS[alias] = new_group_list


def parse_serv(arr, filename, lineno):
	return parse_service(arr, filename, lineno)


def parse_service(arr, filename, lineno):
	if len(arr) < 3:
		raise ParseError("%s:%d: '%s' requires at least 2 arguments: the service alias and at least 1 property" % (filename, lineno, arr[0]))
	
	alias = arr[1]
	if alias == 'any':
		raise ParseError("%s:%d: 'any' is a reserved word" % (filename, lineno))
	
	if firewater.globals.SERVICES.has_key(alias):
		raise ParseError("%s:%d: redefinition of service %s" % (filename, lineno, alias))
	
	obj = firewater.service.ServiceObject(alias)
	
	if arr[2] in firewater.globals.KNOWN_PROTOCOLS:
		obj.proto = arr.pop(2)
	
	if len(arr) < 3:
		raise ParseError("%s:%d: missing service or port number" % (filename, lineno))
	
	if string.find(string.digits, arr[2][0]) > -1:
		# treat as port number or range
		if string.find(arr[2], '-') > -1:
			# treat as port range
			port_range = arr[2]
			
			port_arr = string.split(port_range, '-')
			if len(port_arr) != 2:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			try:
				obj.port = int(port_arr[0])
			except ValueError:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			try:
				obj.endport = int(port_arr[1])
			except ValueError:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			if obj.port < -1 or obj.port > 65535:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			if obj.endport < -1 or obj.endport > 65535 or obj.endport < obj.port:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
		
		elif string.find(arr[2], ':') > -1:
			# treat as port range (same code as above, split by ':') (yeah stupid, I know)
			port_range = arr[2]
			
			port_arr = string.split(port_range, ':')
			if len(port_arr) != 2:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			try:
				obj.port = int(port_arr[0])
			except ValueError:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			try:
				obj.endport = int(port_arr[1])
			except ValueError:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			if obj.port < -1 or obj.port > 65535:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
			
			if obj.endport < -1 or obj.endport > 65535 or obj.endport < obj.port:
				raise ParseError("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
		
		else:
			# single port number
			try:
				obj.port = int(arr[2])
			except ValueError:
				raise ParseError("%s:%d: invalid port number '%s'" % (filename, lineno, arr[2]))
	
	else:
		if arr[2] == alias:
			raise ParseError("%s:%d: service %s references back to itself" % (filename, lineno))
		
		if firewater.globals.SERVICES.has_key(arr[2]):
			obj2 = firewater.globals.SERVICES[arr[2]]
		
			# copy the other service object
			if not obj.proto:
				obj.proto = obj2.proto
			
			obj.port = obj2.port
			obj.endport = obj2.endport
			obj.iface = obj2.iface
		
		else:
			# treat as system service name
			obj.port = firewater.service.servbyname(arr[2])
			if obj.port == None:
				raise ParseError("%s:%d: no such service '%s'" % (filename, lineno, arr[2]))
	
	if len(arr) > 3:
		if arr[3] in ('iface', 'interface'):
			if len(arr) == 5:
				# interface-specific service
				iface = arr[4]
				if firewater.globals.INTERFACES.has_key(iface):
					obj.iface = firewater.globals.INTERFACES[iface]
				else:
					# treat as real system interface
					obj.iface = []
					obj.iface.append(arr[4])
			
			else:
				raise ParseError("%s:%d: too many arguments to '%s'" % (filename, lineno, arr[0]))
	
	debug('new service: %s:%s' % (alias, obj))
	
	firewater.globals.SERVICES[alias] = obj


def parse_chain(arr, filename, lineno):
	if len(arr) < 2:
		raise ParseError("%s:%d: syntax error" % (filename, lineno))
	
	chain = arr[1]
	
	if not chain in ('incoming', 'outgoing', 'forwarding'):
		raise ParseError("%s:%d: syntax error: unknown chain '%s'" % (filename, lineno, chain))
	
	if len(arr) == 5:
		if arr[2] != 'default' or arr[3] != 'policy':
			raise ParseError("%s:%d: syntax error" % (filename, lineno))
		
		policy = arr[4]
		
		debug('policy == %s' % policy)

		if not policy in ('allow', 'deny', 'accept', 'drop'):
			raise ParseError("%s:%d: syntax error: unknown policy '%s'" % (filename, lineno, policy))
		
		# allow for common aliases to be used here
		if policy == 'accept':
			policy = 'allow'
		
		if policy == 'drop':
			policy = 'deny'
		
		debug('set chain %s policy %s' % (chain, policy))
		
		# emit default policy setting code
		bytecode = firewater.bytecode.ByteCode()
		bytecode.set_policy(filename, lineno, chain, policy)
		firewater.globals.BYTECODE.append(bytecode)
	
	else:
		if len(arr) == 2:
			# change the current chain
			debug('set current chain %s' % chain)
		
			bytecode = firewater.bytecode.ByteCode()
			bytecode.set_chain(filename, lineno, chain)
			firewater.globals.BYTECODE.append(bytecode)
			
		else:
			raise ParseError("%s:%d: syntax error" % (filename, lineno))


def _parse_rule(arr, filename, lineno):
	'''parse a rule
	
	rule syntax:
	
	allow|deny|reject [<proto>] [from <source> [port <service>]] \
	    [to <dest> [port <service>]] [on [interface|iface] <iface> [interface]]'''
	
	allow = arr.pop(0)
	
	if len(arr) < 1:
		raise ParseError("%s:%d: syntax error, premature end of line" % (filename, lineno))
	
	proto = None
	if arr[0] in firewater.globals.KNOWN_PROTOCOLS:
		proto = arr.pop(0)
	
	if len(arr) <= 1:
		raise ParseError("%s:%d: syntax error, premature end of line" % (filename, lineno))
	
	# the line can be parsed using tokens
	
	source_addr = None
	source_port = None
	dest_addr = None
	dest_port = None
	interface = None
	
	while len(arr) > 0:
		token = arr.pop(0)
		
		if len(arr) < 1:
			raise ParseError("%s:%d: syntax error, premature end of line" % (filename, lineno))
		
		if token == 'from':
			if source_addr != None:
				raise ParseError("%s:%d: syntax error ('from' is used multiple times)" % (filename, lineno))
			
			source_addr = arr.pop(0)
			
			if len(arr) > 0:
				# check for source port
				if arr[0] == 'port':
					arr.pop(0)
					
					if len(arr) < 1:
						raise ParseError("%s:%d: syntax error, premature end of line" % (filename, lineno))
					
					source_port = arr.pop(0)
			
			continue
		
		elif token == 'to':
			if dest_addr != None:
				raise ParseError("%s:%d: syntax error ('to' is used multiple times)" % (filename, lineno))
			
			dest_addr = arr.pop(0)
			
			if len(arr) > 0:
				# check for dest port
				if arr[0] == 'port':
					arr.pop(0)
					
					if len(arr) < 1:
						raise ParseError("%s:%d: syntax error, premature end of line" % (filename, lineno))
					
					dest_port = arr.pop(0)
			
			continue
		
		elif token == 'on':
			if interface != None:
				raise ParseError("%s:%d: syntax error ('on' is used multiple times)" % (filename, lineno))
			
			if arr[0] in ('interface', 'iface'):
				arr.pop(0)
				
				if len(arr) < 1:
					raise ParseError("%s:%d: syntax error, premature end of line" % (filename, lineno))
			
			interface = arr.pop(0)
			
			if len(arr) > 0 and arr[0] in ('interface', 'iface'):
				arr.pop(0)
			
			continue
		
		else:
			raise ParseError("%s:%d: syntax error, unknown token '%s'" % (filename, lineno, token))
	
	debug('rule {')
	debug('  %s proto %s' % (allow, proto))
	debug('  source (%s, %s)' % (source_addr, source_port))
	debug('  dest   (%s, %s)' % (dest_addr, dest_port))
	debug('  iface   %s' % interface)
	debug('}')
	
	sources = _parse_rule_address(filename, lineno, source_addr)
	source_port = _parse_rule_service(filename, lineno, source_port)
	destinations = _parse_rule_address(filename, lineno, dest_addr)
	dest_port = _parse_rule_service(filename, lineno, dest_port)
	ifaces = _parse_rule_interfaces(filename, lineno, interface)
	
	debug('rule got {')
	debug('  sources: ' + str(sources))
	debug('  port: ' + str(source_port))
	debug('  destinations: ' + str(destinations))
	debug('  port: ' + str(dest_port))
	debug('  ifaces: ' + str(ifaces))
	debug('}')
	
	if not proto and (source_port.port > 0 or dest_port.port > 0):
		if source_port.port > 0 and source_port.proto:
			proto = source_port.proto

		if dest_port.port > 0 and dest_port.proto:
			proto = dest_port.proto

		if not proto:
			raise ParseError("%s:%d: missing protocol" % (filename, lineno))
	
	#
	# save the rule in globals.BYTECODE[]
	# the output statements are generated later, if there were no parse errors
	#
	
	for src in sources:
		for dest in destinations:
			if not ifaces:
				debug('%s:%d: %s %s %s eq %s %s eq %s' % (filename, lineno, allow, proto, src, source_port, dest, dest_port))
				bytecode = firewater.bytecode.ByteCode()
				bytecode.set_rule(filename, lineno, allow, proto, src, source_port, dest, dest_port, None)
				firewater.globals.BYTECODE.append(bytecode)
			else:
				for iface in ifaces:
					debug('%s:%d: %s %s %s eq %s %s eq %s on %s' % (filename, lineno, allow, proto, src, source_port, dest, dest_port, iface))
					bytecode = firewater.bytecode.ByteCode()
					bytecode.set_rule(filename, lineno, allow, proto, src, source_port, dest, dest_port, iface)
					firewater.globals.BYTECODE.append(bytecode)


def _parse_rule_service(filename, lineno, service):
	'''returns ServiceObject for service'''
	
	if not service or service == 'any':
		return firewater.service.ServiceObject()
	
	if string.find(string.digits, service[0]) > -1:
		# numeric service given
		try:
			service_port = int(service)
		except ValueError:
			raise ParseError("%s:%d: syntax error in number '%s'" % (filename, lineno, service))
		
		return firewater.service.ServiceObject(service, service_port)
	
	if firewater.globals.SERVICES.has_key(service):
		# previously defined service
		return firewater.globals.SERVICES[service]
	
	# system service
	service_port = firewater.service.servbyname(service)
	if service_port == None:
		raise ParseError("%s:%d: unknown service '%s'" % (filename, lineno, service))
	
	return firewater.service.ServiceObject(service, service_port)


def _parse_rule_address(filename, lineno, address):
	'''returns list of addresses'''
	
	address_list = []
	
	if not address or address == 'any':
		address_list.append('0.0.0.0/0')
		return address_list
	
	if firewater.globals.HOSTS.has_key(address):
		address_list.extend(firewater.globals.HOSTS[address])
		return address_list
	
	# treat as IP address or fqdn
	if string.find(address, ':') > -1:
		# treat as IPv6 address
		address_list.append(address)
		return address_list
	
	if string.find(address, '/') > -1:
		# treat as network range
		a = string.split(address, '/')
		if len(a) != 2:
			raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, address))
		
		if not _is_ipv4_address(a[0]):
			raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, address))
		
		try:
			bits = int(a[1])
		except ValueError:
			raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, address))
		
		if bits < 0 or bits > 32:
			raise ParseError("%s:%d: invalid address range '%s'" % (filename, lineno, address))
		
		address_list.append(address)
		return address_list
	
	if _is_ipv4_address(address):
		address_list.append(address)
		return address_list
	
	# treat as fqdn
	address_list = firewater.resolv.resolv(address)
	if not address_list:	# error
		raise ParseError("%s:%d: failed to resolve '%s'" % (filename, lineno, address))
	
	return address_list


def _parse_rule_interfaces(filename, lineno, interface):
	iface_list = []
	
	if not interface or interface == 'any':
		return iface_list
	
	if firewater.globals.INTERFACES.has_key(interface):
		iface_list.extend(firewater.globals.INTERFACES[interface])
		return iface_list
	
	iface_list.append(interface)
	return iface_list


def parse_allow(arr, filename, lineno):
	_parse_rule(arr, filename, lineno)


def parse_deny(arr, filename, lineno):
	_parse_rule(arr, filename, lineno)


def parse_reject(arr, filename, lineno):
	_parse_rule(arr, filename, lineno)


def parse_echo(arr, filename, lineno):
	if len(arr) <= 1:
		str = ''
	else:
		str = string.join(arr[1:])
	
	bytecode = firewater.bytecode.ByteCode()
	bytecode.set_echo(filename, lineno, str)
	firewater.globals.BYTECODE.append(bytecode)


def parse_verbatim(arr, filename, lineno):
	global IN_VERBATIM
	
	if len(arr) > 1:
		raise ParseError("%s:%d: syntax error, 'verbatim' does not take any arguments" % (filename, lineno))
	
	debug('in verbatim')
	
	IN_VERBATIM = True
	firewater.globals.VERBATIM = []


def parse_end(arr, filename, lineno):
	global IN_VERBATIM
	
	if len(arr) > 2:
		raise ParseError("%s:%d: syntax error, 'end' takes only one argument" % (filename, lineno))
	
	if arr[1] == 'verbatim':
		if not IN_VERBATIM:
			raise ParseError("%s:%d: 'end' can not be used here" % (filename, lineno))
		
		debug('end verbatim')
		
		IN_VERBATIM = False
		
		bytecode_end_verbatim = firewater.globals.BYTECODE.pop()
		
		bytecode = firewater.bytecode.ByteCode()
		bytecode.set_verbatim(filename, lineno, firewater.globals.VERBATIM)
		firewater.globals.BYTECODE.append(bytecode)
		
		firewater.globals.BYTECODE.append(bytecode_end_verbatim)
		
	else:
		raise ParseError("%s:%d: unknown argument '%s' to 'end'" % (filename, lineno, arr[1]))


def parse_define(arr, filename, lineno):
	if len(arr) != 2:
		raise ParseError("%s:%d: syntax error, 'define' takes only one argument: a symbol to define" % (filename, lineno))
	
	debug('parser: define "%s"' % arr[1])
	
	bytecode = firewater.bytecode.ByteCode()
	bytecode.set_define(filename, lineno, arr[1])
	firewater.globals.BYTECODE.append(bytecode)


def parse_ifdef(arr, filename, lineno):
	global IFDEF_LEVEL
	
	if len(arr) != 2:
		raise ParseError("%s:%d: syntax error, 'ifdef' takes only one argument: a defined symbol" % (filename, lineno))
	
	bytecode = firewater.bytecode.ByteCode()
	bytecode.set_ifdef(filename, lineno, arr[1])
	firewater.globals.BYTECODE.append(bytecode)
	
	IFDEF_LEVEL = IFDEF_LEVEL + 1


def parse_ifndef(arr, filename, lineno):
	global IFDEF_LEVEL
	
	if len(arr) != 2:
		raise ParseError("%s:%d: syntax error, 'ifndef' takes one argument: a defined symbol" % (filename, lineno))
	
	bytecode = firewater.bytecode.ByteCode()
	bytecode.set_ifndef(filename, lineno, arr[1])
	firewater.globals.BYTECODE.append(bytecode)
	
	IFDEF_LEVEL = IFDEF_LEVEL + 1


def parse_endif(arr, filename, lineno):
	global IFDEF_LEVEL
	
	if len(arr) != 1:
		raise ParseError("%s:%d: syntax error, 'endif' takes no arguments" % (filename, lineno))
	
	bytecode = firewater.bytecode.ByteCode()
	bytecode.set_endif(filename, lineno)
	firewater.globals.BYTECODE.append(bytecode)
	
	IFDEF_LEVEL = IFDEF_LEVEL - 1
	if IFDEF_LEVEL < 0:
		raise ParseError("%s:%d: error, endif reached without matching ifdef" % (filename, lineno))


def parse_exit(arr, filename, lineno):
	if len(arr) > 2:
		raise ParseError("%s:%d: syntax error, too many arguments to 'exit'" % (filename, lineno))
	
	exit_code = 0
	
	if len(arr) == 2:
		try:
			exit_code = int(arr[1])
		except ValueError:
			raise ParseError("%s:%d: syntax error, 'exit' may take an integer argument" % (filename, lineno))
	
	bytecode = firewater.bytecode.ByteCode()
	bytecode.set_exit(filename, lineno, exit_code)
	firewater.globals.BYTECODE.append(bytecode)


# EOB
