#
#	firewater/parser.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2003-2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

#
#	To make a new keyword for the input file, simply define a
#	Parser method like: def parse_xxx(self, arr, filename, lineno):
#	and it will just work (magic trick with getattr(self, functionname))
#

import firewater.globals
import firewater.resolv
import firewater.service
import firewater.bytecode

from firewater.lib import *

import os
import sys
import string


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


class Parser:
	'''class that parses an input file'''
	
	def __init__(self):
		self.filename = None
		self.file = None
		self.lineno = 0
		self.full_line = None
		self.line = None
		self.comment = None
		self.arr = None
		self.keyword = None
		self.errors = 0
		self.in_verbatim = False
		self.verbatim_text = None
		self.ifdef_stack = None
		self.else_stack = None
	
	def __repr__(self):
		return '%s:%d' % (self.filename, self.lineno)
	
	def open(self, filename):
		self.filename = filename
		self.file = open(self.filename, 'r')
		self.lineno = 0
		self.verbatim_text = []
		
		# is the ifdef true? may we execute statements?
		self.ifdef_stack = [ True ]
		
		# can we have an 'else' statement now?
		self.else_stack = [ False ]
	
	def close(self):
		self.file.close()
		self.file = None
		
		if self.in_verbatim:
			ParseError("%s: missing 'end verbatim' statement" % self).perror()
		
		self.lineno = 0
		self.full_line = None
		self.line = None
		self.comment = None
		self.arr = None
		self.keyword = None
		self.in_verbatim = False
		self.verbatim_text = None
		self.ifdef_stack = None
		self.else_stack = None
	
	def getline(self):
		'''read statement from input file'''
		'''Upon return, self.keyword should be set, as well as other members'''
		'''Returns True when OK, False on EOF'''
		
		self.full_line = None
		self.line = ''
		self.comment = None
		self.arr = None
		self.keyword = None
		
		while True:
			#
			#	read lines from the input file
			#	variable tmp_line is used to be able to do multi-line reads (backslash terminated)
			#
			tmp_line = self.file.readline()
			if not tmp_line:
				return False
			
			self.lineno += 1
			
			if self.in_verbatim:
				# copy verbatim until the statement 'end verbatim' is reached
				verbatim_line = string.strip(tmp_line)
				arr = string.split(string.lower(verbatim_line))
				# it is tested with an array so that both spaces and tabs work
				# note that this shadows the 'end' keyword, but only when in verbatim mode
				if not (len(arr) == 2 and arr[0] == 'end' and arr[1] == 'verbatim'):
					debug('verbatim line == [%s]' % verbatim_line)
					self.verbatim_text.append(verbatim_line)
					continue
			
			n = string.find(tmp_line, '#')
			if n >= 0:
				self.comment = '    ' + string.strip(tmp_line[n:])
				tmp_line = tmp_line[:n]		# strip comment
			else:
				self.comment = ''
			
			tmp_line = string.strip(tmp_line)
			if not tmp_line:
				continue
			
			if tmp_line[-1] == '\\':
				tmp_line = string.strip(tmp_line[:-1])
				self.line = self.line + ' ' + tmp_line
				continue
			
			self.line = self.line + ' ' + tmp_line
			self.full_line = self.line + self.comment
			self.arr = string.split(self.line)
			self.keyword = string.lower(self.arr[0])
			break
		
		return True
	
	def interpret(self):
		'''interpret a line (first call Parser.getline())'''
		'''Returns 0 on success, 1 on error'''
		
		if not self.keyword:
			raise ParseError('%s: no keyword set; invalid parser state' % self)
			self.errors += 1
			return 1
		
		if not self.ifdef_stack[0]:
			if not self.keyword in ('ifdef', 'ifndef', 'else', 'endif'):
				debug("%s: skipping %s" % (self, self.keyword))
				return 0
		
		# get the parser function
		try:
			func = getattr(self, 'parse_%s' % self.keyword)
		except AttributeError:
			stderr("%s: unknown keyword '%s'" % (self, self.keyword))
			self.errors += 1
			return 1
		
		try:
			func()
		except ParseError, (parse_error):
			parse_error.perror()
			self.errors += 1
			return 1
		
		return 0
	
	def insert_comment_line(self):
		'''insert the current line into bytecode as comment'''
		'''(this will be displayed in verbose mode)'''
		
		if self.ifdef_stack[0] or self.keyword in ('ifdef', 'ifndef', 'else', 'endif'):
			bytecode = firewater.bytecode.ByteCode()
			bytecode.set_comment(self.filename, self.lineno, self.full_line)
			firewater.globals.BYTECODE.append(bytecode)
	
	def missing_comma(self, a_list):
		'''lists must be comma-separated, so if this function returns != None
		then it's a syntax error: missing comma after element'''
		
		n = 0
		for elem in a_list:
			arr = string.split(elem)
			if len(arr) > 1:
				return arr[0]
			
			n += 1
		
		return None

	### parser keywords ###
	
	def parse_include(self):
		arr = self.arr
		if len(arr) <= 1:
			raise ParseError("%s: 'include' requires a filename argument" % self)
		
		include_file = string.join(arr[1:])
		
		debug('include %s' % include_file)
		
		try:
			# recursively read the given parse file
			if read_input_file(include_file) > 0:
				raise ParseError("%s: error in included file %s" % (self, include_file))
		
		except IOError:
			raise ParseError("%s: failed to read file '%s'" % (self, include_file))
	
	
	def parse_iface(self):
		self.parse_interface()
	
	
	def parse_interface(self):
		arr = self.arr
		if len(arr) < 3:
			raise ParseError("%s: '%s' requires at least 2 arguments: the interface alias and the real interface name" % (self, self.keyword))
		
		alias = arr[1]
		if alias == 'any':
			raise ParseError("%s: 'any' is a reserved word" % self)
		
		iface_list = string.join(arr[2:])
		iface_list = string.split(iface_list, ',')
		
		elem = self.missing_comma(iface_list)
		if elem != None:
			raise ParseError("%s: missing comma after '%s'" % (self, elem))
		
		if alias in iface_list:
			raise ParseError("%s: interface %s references back to itself" % (self, alias))
		
		if firewater.globals.INTERFACES.has_key(alias):
			raise ParseError("%s: redefinition of interface %s" % (self, alias))
		
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
	
	
	def parse_echo(self):
		arr = self.arr
		if len(arr) <= 1:
			str = ''
		else:
			str = string.join(arr[1:])
		
		bytecode = firewater.bytecode.ByteCode()
		bytecode.set_echo(self.filename, self.lineno, str)
		firewater.globals.BYTECODE.append(bytecode)
	
	
	def parse_host(self):
		arr = self.arr
		if len(arr) < 3:
			raise ParseError("%s: 'host' requires at least 2 arguments: the host alias and the IP address or fqdn" % self)
		
		alias = arr[1]
		if alias == 'any':
			raise ParseError("%s: 'any' is a reserved word" % self)
		
		host_list = string.join(arr[2:])
		host_list = string.replace(host_list, ' ', '')
		host_list = string.replace(host_list, ',,', ',')
		host_list = string.split(host_list, ',')
		
		elem = self.missing_comma(host_list)
		if elem != None:
			raise ParseError("%s: missing comma after '%s'" % (self, elem))
		
		if alias in host_list:
			raise ParseError("%s: host %s references back to itself" % (self, alias))
		
		if firewater.globals.HOSTS.has_key(alias):
			raise ParseError("%s: redefinition of host %s" % (self, alias))
		
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
						raise ParseError("%s: invalid host address '%s'" % (self, host))
					
					if not _is_ipv4_address(a[0]):
						raise ParseError("%s: invalid host address '%s'" % (self, host))
					
					if a[1] != '32':
						raise ParseError("%s: invalid host address '%s'" % (self, host))
					
					pass
				
				elif _is_ipv4_address(host):
					# treat as IPv4 address
					pass
				
				else:
					# treat as fqdn, so resolve the address
					addrs = firewater.resolv.resolv(host)
					if addrs == None:	# error
						raise ParseError("%s: failed to resolve '%s'" % (self, host))
					
					for addr in addrs:
						if not addr in new_host_list:
							new_host_list.append(addr)
					
					continue
				
				if not host in new_host_list:
					new_host_list.append(host)
		
		debug('new host: %s:%s' % (alias, new_host_list))
		
		firewater.globals.HOSTS[alias] = new_host_list
	
	
	def parse_network(self):
		self.parse_range()
	
	
	def parse_range(self):
		arr = self.arr
		if len(arr) < 3:
			raise ParseError("%s: '%s' requires at least 2 arguments: the range alias and the address range" % (self, arr[0]))
		
		alias = arr[1]
		if alias == 'any':
			raise ParseError("%s: 'any' is a reserved word" % self)
		
		ranges_list = string.join(arr[2:])
		ranges_list = string.replace(ranges_list, ' ', '')
		ranges_list = string.replace(ranges_list, ',,', ',')
		ranges_list = string.split(ranges_list, ',')
		
		elem = self.missing_comma(ranges_list)
		if elem != None:
			raise ParseError("%s: missing comma after '%s'" % (self, elem))
		
		if alias in ranges_list:
			raise ParseError("%s: %s %s references back to itself" % (self, arr[0], alias))
		
		# note that ranges are stored in the same way as hosts
		if firewater.globals.HOSTS.has_key(alias):
			raise ParseError("%s: redefinition of %s or host %s" % (self, arr[0], alias))
		
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
						raise ParseError("%s: invalid address range '%s'" % (self, host))
					
					if not _is_ipv4_address(a[0]):
						raise ParseError("%s: invalid address range '%s'" % (self, host))
					
					try:
						bits = int(a[1])
					except ValueError:
						raise ParseError("%s: invalid address range '%s'" % (self, host))
					
					if bits < 0 or bits > 32:
						raise ParseError("%s: invalid address range '%s'" % (self, host))
				
				else:
					raise ParseError("%s: invalid address range '%s'" % (self, host))
				
				if not host in new_ranges_list:
					new_ranges_list.append(host)
		
		debug('new %s: %s:%s' % (arr[0], alias, new_ranges_list))
		
		firewater.globals.HOSTS[alias] = new_ranges_list
	
	
	def parse_group(self):
		arr = self.arr
		if len(arr) < 3:
			raise ParseError("%s: 'group' requires at least 2 arguments: the group alias and at least 1 member" % self)
		
		alias = arr[1]
		if alias == 'any':
			raise ParseError("%s: 'any' is a reserved word" % self)
		
		group_list = string.join(arr[2:], ',')
		group_list = string.replace(group_list, ' ', '')
		group_list = string.replace(group_list, ',,', ',')
		group_list = string.split(group_list, ',')
		
		elem = self.missing_comma(group_list)
		if elem != None:
			raise ParseError("%s: missing comma after '%s'" % (self, elem))
		
		if alias in group_list:
			raise ParseError("%s: range %s references back to itself" % (self, alias))
		
		# note that group are stored in the same way as groups
		if firewater.globals.HOSTS.has_key(alias):
			raise ParseError("%s: redefinition of range or group %s" % (self, alias))
		
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
						raise ParseError("%s: invalid address range '%s'" % (self, group))
					
					if not _is_ipv4_address(a[0]):
						raise ParseError("%s: invalid address range '%s'" % (self, group))
					
					try:
						bits = int(a[1])
					except ValueError:
						raise ParseError("%s: invalid address range '%s'" % (self, group))
					
					if bits < 0 or bits > 32:
						raise ParseError("%s: invalid address range '%s'" % (self, group))
				
				else:
					# treat as fqdn, so resolve the address
					addrs = firewater.resolv.resolv(group)
					if addrs == None:	# error
						raise ParseError("%s: failed to resolve '%s'" % (self, group))
					
					for addr in addrs:
						if not addr in new_group_list:
							new_group_list.append(addr)
					
					continue
				
				if not group in new_group_list:
					new_group_list.append(group)
		
		debug('new group: %s:%s' % (alias, new_group_list))
		
		firewater.globals.HOSTS[alias] = new_group_list
	
	
	def parse_serv(self):
		return self.parse_service()
	
	
	def parse_service(self):
		arr = self.arr
		if len(arr) < 3:
			raise ParseError("%s: '%s' requires at least 2 arguments: the service alias and at least 1 property" % (self, arr[0]))
		
		alias = arr[1]
		if alias == 'any':
			raise ParseError("%s: 'any' is a reserved word" % self)
		
		if firewater.globals.SERVICES.has_key(alias):
			raise ParseError("%s: redefinition of service %s" % (self, alias))
		
		obj = firewater.service.ServiceObject(alias)
		
		if arr[2] in firewater.globals.KNOWN_PROTOCOLS:
			obj.proto = arr.pop(2)
		
		if len(arr) < 3:
			raise ParseError("%s: missing service or port number" % self)
		
		if string.find(string.digits, arr[2][0]) > -1:
			# treat as port number or range
			if string.find(arr[2], '-') > -1:
				# treat as port range
				port_range = arr[2]
				
				port_arr = string.split(port_range, '-')
				if len(port_arr) != 2:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				try:
					obj.port = int(port_arr[0])
				except ValueError:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				try:
					obj.endport = int(port_arr[1])
				except ValueError:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				if obj.port < -1 or obj.port > 65535:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				if obj.endport < -1 or obj.endport > 65535 or obj.endport < obj.port:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
			
			elif string.find(arr[2], ':') > -1:
				# treat as port range (same code as above, split by ':') (yeah stupid, I know)
				port_range = arr[2]
				
				port_arr = string.split(port_range, ':')
				if len(port_arr) != 2:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				try:
					obj.port = int(port_arr[0])
				except ValueError:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				try:
					obj.endport = int(port_arr[1])
				except ValueError:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				if obj.port < -1 or obj.port > 65535:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
				
				if obj.endport < -1 or obj.endport > 65535 or obj.endport < obj.port:
					raise ParseError("%s: invalid port range '%s'" % (self, port_range))
			
			else:
				# single port number
				try:
					obj.port = int(arr[2])
				except ValueError:
					raise ParseError("%s: invalid port number '%s'" % (self, arr[2]))
		
		else:
			if arr[2] == alias:
				raise ParseError("%s: service %s references back to itself" % self)
			
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
					raise ParseError("%s: no such service '%s'" % (self, arr[2]))
		
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
					raise ParseError("%s: too many arguments to '%s'" % (self, arr[0]))
		
		debug('new service: %s:%s' % (alias, obj))
		
		firewater.globals.SERVICES[alias] = obj
	
	
	def parse_chain(self):
		arr = self.arr
		if len(arr) < 2:
			raise ParseError("%s: syntax error" % self)
		
		chain = arr[1]
		
		if not chain in ('incoming', 'outgoing', 'forwarding'):
			raise ParseError("%s: syntax error: unknown chain '%s'" % (self, chain))
		
		if len(arr) == 5:
			if arr[2] != 'default' or arr[3] != 'policy':
				raise ParseError("%s: syntax error" % self)
			
			policy = arr[4]
			
			debug('policy == %s' % policy)
			
			if not policy in ('allow', 'deny', 'accept', 'drop'):
				raise ParseError("%s: syntax error: unknown policy '%s'" % (self, policy))
			
			# allow for common aliases to be used here
			if policy == 'accept':
				policy = 'allow'
			
			if policy == 'drop':
				policy = 'deny'
			
			debug('set chain %s policy %s' % (chain, policy))
			
			# emit default policy setting code
			bytecode = firewater.bytecode.ByteCode()
			bytecode.set_policy(self.filename, self.lineno, chain, policy)
			firewater.globals.BYTECODE.append(bytecode)
		
		else:
			if len(arr) == 2:
				# change the current chain
				debug('set current chain %s' % chain)
				
				bytecode = firewater.bytecode.ByteCode()
				bytecode.set_chain(self.filename, self.lineno, chain)
				firewater.globals.BYTECODE.append(bytecode)
			
			else:
				raise ParseError("%s: syntax error" % self)
	
	
	def _parse_rule(self):
		'''parse a rule
		
		rule syntax:
		
		allow|deny|reject [<proto>] [from <source> [port <service>]] \
		[to <dest> [port <service>]] [on [interface|iface] <iface> [interface]]'''
		
		arr = self.arr
		allow = arr.pop(0)
		
		if len(arr) < 1:
			raise ParseError("%s: syntax error, premature end of line" % self)
		
		proto = None
		if arr[0] in firewater.globals.KNOWN_PROTOCOLS:
			proto = arr.pop(0)
		
		if len(arr) <= 1:
			raise ParseError("%s: syntax error, premature end of line" % self)
		
		# the line can be parsed using tokens
		
		source_addr = None
		source_port = None
		dest_addr = None
		dest_port = None
		interface = None
		
		while len(arr) > 0:
			token = arr.pop(0)
			
			if len(arr) < 1:
				raise ParseError("%s: syntax error, premature end of line" % self)
			
			if token == 'from':
				if source_addr != None:
					raise ParseError("%s: syntax error ('from' is used multiple times)" % self)
				
				source_addr = arr.pop(0)
				
				if len(arr) > 0:
					# check for source port
					if arr[0] == 'port':
						arr.pop(0)
						
						if len(arr) < 1:
							raise ParseError("%s: syntax error, premature end of line" % self)
						
						source_port = arr.pop(0)
				
				continue
			
			elif token == 'to':
				if dest_addr != None:
					raise ParseError("%s: syntax error ('to' is used multiple times)" % self)
				
				dest_addr = arr.pop(0)
				
				if len(arr) > 0:
					# check for dest port
					if arr[0] == 'port':
						arr.pop(0)
						
						if len(arr) < 1:
							raise ParseError("%s: syntax error, premature end of line" % self)
						
						dest_port = arr.pop(0)
				
				continue
			
			elif token == 'on':
				if interface != None:
					raise ParseError("%s: syntax error ('on' is used multiple times)" % self)
				
				if arr[0] in ('interface', 'iface'):
					arr.pop(0)
					
					if len(arr) < 1:
						raise ParseError("%s: syntax error, premature end of line" % self)
				
				interface = arr.pop(0)
				
				if len(arr) > 0 and arr[0] in ('interface', 'iface'):
					arr.pop(0)
				
				continue
			
			else:
				raise ParseError("%s: syntax error, unknown token '%s'" % (self, token))
		
		debug('rule {')
		debug('  %s proto %s' % (allow, proto))
		debug('  source (%s, %s)' % (source_addr, source_port))
		debug('  dest   (%s, %s)' % (dest_addr, dest_port))
		debug('  iface   %s' % interface)
		debug('}')
		
		sources = self._parse_rule_address(source_addr)
		source_port = self._parse_rule_service(source_port)
		destinations = self._parse_rule_address(dest_addr)
		dest_port = self._parse_rule_service(dest_port)
		ifaces = self._parse_rule_interfaces(interface)
		
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
				raise ParseError("%s: missing protocol" % self)
		
		#
		# save the rule in globals.BYTECODE[]
		# the output statements are generated later, if there were no parse errors
		#
		
		for src in sources:
			for dest in destinations:
				if not ifaces:
					debug('%s: %s %s %s eq %s %s eq %s' % (self, allow, proto, src, source_port, dest, dest_port))
					bytecode = firewater.bytecode.ByteCode()
					bytecode.set_rule(self.filename, self.lineno, allow, proto, src, source_port, dest, dest_port, None)
					firewater.globals.BYTECODE.append(bytecode)
				else:
					for iface in ifaces:
						debug('%s: %s %s %s eq %s %s eq %s on %s' % (self, allow, proto, src, source_port, dest, dest_port, iface))
						bytecode = firewater.bytecode.ByteCode()
						bytecode.set_rule(self.filename, self.lineno, allow, proto, src, source_port, dest, dest_port, iface)
						firewater.globals.BYTECODE.append(bytecode)
	
	
	def _parse_rule_service(self, service):
		'''returns ServiceObject for service'''
		
		if not service or service == 'any':
			return firewater.service.ServiceObject()
		
		if string.find(string.digits, service[0]) > -1:
			# numeric service given
			try:
				service_port = int(service)
			except ValueError:
				raise ParseError("%s: syntax error in number '%s'" % (self, service))
			
			return firewater.service.ServiceObject(service, service_port)
		
		if firewater.globals.SERVICES.has_key(service):
			# previously defined service
			return firewater.globals.SERVICES[service]
		
		# system service
		service_port = firewater.service.servbyname(service)
		if service_port == None:
			raise ParseError("%s: unknown service '%s'" % (self, service))
		
		return firewater.service.ServiceObject(service, service_port)


	def _parse_rule_address(self, address):
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
				raise ParseError("%s: invalid address range '%s'" % (self, address))
			
			if not _is_ipv4_address(a[0]):
				raise ParseError("%s: invalid address range '%s'" % (self, address))
			
			try:
				bits = int(a[1])
			except ValueError:
				raise ParseError("%s: invalid address range '%s'" % (self, address))
			
			if bits < 0 or bits > 32:
				raise ParseError("%s: invalid address range '%s'" % (self, address))
			
			address_list.append(address)
			return address_list
		
		if _is_ipv4_address(address):
			address_list.append(address)
			return address_list
		
		# treat as fqdn
		address_list = firewater.resolv.resolv(address)
		if not address_list:	# error
			raise ParseError("%s: failed to resolve '%s'" % (self, address))
		
		return address_list
	
	
	def _parse_rule_interfaces(self, interface):
		iface_list = []
		
		if not interface or interface == 'any':
			return iface_list
		
		if firewater.globals.INTERFACES.has_key(interface):
			iface_list.extend(firewater.globals.INTERFACES[interface])
			return iface_list
		
		iface_list.append(interface)
		return iface_list
	
	
	def parse_allow(self):
		self._parse_rule()
	
	
	def parse_deny(self):
		self._parse_rule()
	
	
	def parse_reject(self):
		self._parse_rule()
	
	
	def parse_verbatim(self):
		arr = self.arr
		if len(arr) > 1:
			raise ParseError("%s: syntax error, 'verbatim' does not take any arguments" % self)
		
		debug('in verbatim')
		
		self.in_verbatim = True
		self.verbatim_text = []
	
	
	def parse_end(self):
		arr = self.arr
		if len(arr) > 2:
			raise ParseError("%s: syntax error, 'end' takes only one argument" % self)
		
		if arr[1] == 'verbatim':
			if not self.in_verbatim:
				raise ParseError("%s: 'end' can not be used here" % self)
			
			debug('end verbatim')
			
			self.in_verbatim = False
			
			bytecode_end_verbatim = firewater.globals.BYTECODE.pop()
			
			bytecode = firewater.bytecode.ByteCode()
			bytecode.set_verbatim(self.filename, self.lineno, self.verbatim_text)
			firewater.globals.BYTECODE.append(bytecode)
			
			firewater.globals.BYTECODE.append(bytecode_end_verbatim)
			
		else:
			raise ParseError("%s: unknown argument '%s' to 'end'" % (self, arr[1]))
	
	
	def parse_define(self):
		arr = self.arr
		if len(arr) != 2:
			raise ParseError("%s: syntax error, 'define' takes only one argument: a symbol to define" % self)
		
		debug('parser: define "%s"' % arr[1])
		firewater.globals.DEFINES.append(arr[1])
	
	
	def parse_ifdef(self):
		arr = self.arr
		if len(arr) != 2:
			raise ParseError("%s: syntax error, 'ifdef' takes only one argument: a defined symbol" % self)
		
		if self.ifdef_stack[0]:
			self.ifdef_stack.insert(0, arr[1] in firewater.globals.DEFINES)
		else:
			self.ifdef_stack.insert(0, False)
		
		self.else_stack.insert(0, True)
	
	
	def parse_ifndef(self):
		arr = self.arr
		if len(arr) != 2:
			raise ParseError("%s: syntax error, 'ifdef' takes only one argument: a defined symbol" % self)
		
		if self.ifdef_stack[0]:
			self.ifdef_stack.insert(0, not arr[1] in firewater.globals.DEFINES)
		else:
			self.ifdef_stack.insert(0, False)
		
		self.else_stack.insert(0, True)
	
	
	def parse_else(self):
		arr = self.arr
		if len(arr) > 1:
			raise ParseError("%s: syntax error, 'else' takes no arguments" % self)
		
		if len(self.ifdef_stack) <= 1 or not self.else_stack[0]:
			raise ParseError("%s: error, 'else' without ifdef or ifndef" % self)
		
		v = self.ifdef_stack.pop(0)
		if self.ifdef_stack[0]:
			self.ifdef_stack.insert(0, not v)
		else:
			self.ifdef_stack.insert(0, False)
		
		self.else_stack[0] = False


	def parse_endif(self):
		arr = self.arr
		if len(arr) > 1:
			raise ParseError("%s: syntax error, 'endif' takes no arguments" % self)
		
		if len(self.ifdef_stack) <= 1:
			raise ParseError("%s: error, 'endif' without ifdef or ifndef" % self)
		
		self.ifdef_stack.pop(0)
		self.else_stack.pop(0)
	
	
	def parse_exit(self):
		arr = self.arr
		if len(arr) > 2:
			raise ParseError("%s: syntax error, too many arguments to 'exit'" % self)
		
		exit_code = 0
		
		if len(arr) == 2:
			try:
				exit_code = int(arr[1])
			except ValueError:
				raise ParseError("%s: syntax error, 'exit' may take an integer argument" % self)
		
		bytecode = firewater.bytecode.ByteCode()
		bytecode.set_exit(self.filename, self.lineno, exit_code)
		firewater.globals.BYTECODE.append(bytecode)


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


def read_input_file(filename):	# throws IOError
	'''read a (included) input file
		Returns 0 on success, or error count on errors'''
	
	errors = 0
	
	parser = Parser()
	parser.open(filename)
	
	while parser.getline():
		parser.insert_comment_line()
		parser.interpret()
	
	if len(parser.ifdef_stack) > 1:
		ParseError("%s: missing 'endif' statement" % parser).perror()
		errors += 1
	
	parser.close()
	errors = errors + parser.errors
	
	debug('errors == %d' % errors)
	return errors


# EOB
