#! /usr/bin/env python
#
#	firewater_parser.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2003-2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

#
#	To make a new keyword for the input file, simply define a
#	function here like: def parse_xxx(arr, filename, lineno):
#	and it will just work (magic trick with getattr(module, functionname))
#

import  firewater_globals

from firewater_lib import *

import firewater_resolv
import firewater_service

import os
import sys
import string


def read_input_file(filename):
	'''read a (included) input file
	Returns 0 on success, or error count on errors'''
	
	try:
		f = open(filename, 'r')
	except IOError, reason:
		stderr("failed to read input file '%s' : %s" % (filename, reason))
		return 1
	
	this_module = sys.modules['firewater_parser']
	
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
		
		n = string.find(tmp_line, '#')
		if n >= 0:
			tmp_line = tmp_line[:n]		# strip comment
		
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
		
		line = ''	# <-- line is being reset here; use arr[] from here on
		
		if len(arr) <= 1:
			stderr('%s:%d: syntax error' % (filename, lineno))
			errors = errors + 1
			continue
		
		keyword = string.lower(arr[0])
		
		# get the parser function
		try:
			func = getattr(this_module, 'parse_%s' % keyword)
		except AttributeError:
			stderr("%s:%d: unknown keyword '%s'" % (filename, lineno, keyword))
			errors = errors + 1
			continue
		
		errors = errors + func(arr, filename, lineno)
	
	f.close()
	return errors


#
# parse_ functions return the number of errors in the line
# This enables the 'include' keyword to return more than 1 error
#

def _parse_boolean(param, value, filename, lineno):
	value = string.lower(value)
	if value in firewater_param.BOOLEAN_VALUE_TRUE:
		return (0, True)
	
	elif value in firewater_param.BOOLEAN_VALUE_FALSE:
		return (0, False)
	
	stderr('%s:%d: invalid argument for %s' % (filename, lineno, param))
	return (1, False)


def _parse_integer(param, value, filename, lineno, radix = 10):
	try:
		n = int(value, radix)
	except ValueError:
		stderr('%s:%d: invalid argument for %s' % (filename, lineno, param))
		return (1, 0)
	
	return (0, n)


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
	debug('include %s' % filename)
	# recursively read the given parse file
	return read_input_file(arr[1])


def parse_iface(arr, filename, lineno):
	return parse_interface(arr, filename, lineno)


def parse_interface(arr, filename, lineno):
	if len(arr) < 3:
		stderr("%s:%d: '%s' requires at least 2 arguments: the interface alias and the real interface name" % (filename, lineno, arr[0]))
		return 1
	
	alias = arr[1]
	
	iface_list = string.join(arr[2:])
	iface_list = string.split(iface_list, ',')
	
	if alias in iface_list:
		stderr("%s:%d: interface %s references back to itself" % (filename, lineno, alias))
		return 1
	
	if firewater_globals.INTERFACES.has_key(alias):
		stderr("%s:%d: redefinition of interface %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_iface_list = []
	while len(iface_list) > 0:
		iface = iface_list.pop(0)
		if firewater_globals.INTERFACES.has_key(iface):
			iface_list.extend(firewater_globals.INTERFACES[iface])
		else:
			# treat as real system interface name
			if not iface in new_iface_list:
				new_iface_list.append(iface)
	
	debug('new interface: %s:%s' % (alias, new_iface_list))
	
	firewater_globals.INTERFACES[alias] = new_iface_list
	
	all_ifaces = firewater_globals.INTERFACES['all']
	for iface in new_iface_list:
		if not iface in all_ifaces:
			all_ifaces.append(iface)
	
	return 0


def parse_debug(arr, filename, lineno):
	if len(arr) < 2:
		stderr("%s:%d: usage: debug interfaces|hosts|services" % (filename, lineno))
		return 1
	
	if arr[1] in ('iface', 'interfaces'):
		print 'firewater_globals.INTERFACES ==', firewater_globals.INTERFACES
		print
		return 0
	
	elif arr[1] in ('host', 'hosts'):
		print 'firewater_globals.HOSTS ==', firewater_globals.HOSTS
		print
		return 0
	
	elif arr[1] in ('services', 'serv'):
		print 'firewater_globals.SERVICES ==', firewater_globals.SERVICES
		print
		return 0
	
	stderr("%s:%d: don't know how to debug '%s'" % (filename, lineno, arr[1]))
	return 1


def parse_host(arr, filename, lineno):
	if len(arr) < 3:
		stderr("%s:%d: 'host' requires at least 2 arguments: the host alias and the IP address or fqdn" % (filename, lineno))
		return 1
	
	alias = arr[1]
	
	host_list = string.join(arr[2:])
	host_list = string.replace(host_list, ' ', '')
	host_list = string.replace(host_list, ',,', ',')
	host_list = string.split(host_list, ',')
	
	if alias in host_list:
		stderr("%s:%d: host %s references back to itself" % (filename, lineno, alias))
		return 1
	
	if firewater_globals.HOSTS.has_key(alias):
		stderr("%s:%d: redefinition of host %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_host_list = []
	while len(host_list) > 0:
		host = host_list.pop(0)
		if firewater_globals.HOSTS.has_key(host):
			host_list.extend(firewater_globals.HOSTS[host])
		else:
			# treat as IP address or fqdn
			if string.find(host, ':') > -1:
				# treat as IPv6 address
				pass
			
			elif string.find(host, '/') > -1:
				# treat as network range
				a = string.split(host, '/')
				if len(a) != 2:
					stderr("%s:%d: invalid host address '%s'" % (filename, lineno, host))
					return 1
				
				if not _is_ipv4_address(a[0]):
					stderr("%s:%d: invalid host address '%s'" % (filename, lineno, host))
					return 1
				
				if a[1] != '32':
					stderr("%s:%d: invalid host address '%s'" % (filename, lineno, host))
					return 1
				
				pass
			
			elif _is_ipv4_address(host):
				# treat as IPv4 address
				pass
			
			else:
				# treat as fqdn, so resolve the address
				addrs = firewater_resolv.resolv(host)
				if addrs == None:	# error
					stderr("%s:%d: failed to resolve '%s'" % (filename, lineno, host))
					return 1
				
				for addr in addrs:
					if not addr in new_host_list:
						new_host_list.append(addr)
				
				continue
			
			if not host in new_host_list:
				new_host_list.append(host)
	
	debug('new host: %s:%s' % (alias, new_host_list))
	
	firewater_globals.HOSTS[alias] = new_host_list
	
	return 0


def parse_range(arr, filename, lineno):
	if len(arr) < 3:
		stderr("%s:%d: 'range' requires at least 2 arguments: the range alias and the address range" % (filename, lineno))
		return 1
	
	alias = arr[1]
	
	ranges_list = string.join(arr[2:])
	ranges_list = string.replace(ranges_list, ' ', '')
	ranges_list = string.replace(ranges_list, ',,', ',')
	ranges_list = string.split(ranges_list, ',')
	
	if alias in ranges_list:
		stderr("%s:%d: range %s references back to itself" % (filename, lineno, alias))
		return 1
	
	# note that ranges are stored in the same way as hosts
	if firewater_globals.HOSTS.has_key(alias):
		stderr("%s:%d: redefinition of range or host %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_ranges_list = []
	while len(ranges_list) > 0:
		# 'range' is a Python keyword ... so I use 'host' instead (confusing huh?)
		host = ranges_list.pop(0)
		if firewater_globals.HOSTS.has_key(host):
			ranges_list.extend(firewater_globals.HOSTS[host])
		else:
			# treat as IP address or fqdn
			if string.find(host, ':') > -1:
				# treat as IPv6 address
				pass
			
			elif string.find(host, '/') > -1:
				# treat as network range
				a = string.split(host, '/')
				if len(a) != 2:
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, host))
					return 1
				
				if not _is_ipv4_address(a[0]):
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, host))
					return 1
				
				try:
					bits = int(a[1])
				except ValueError:
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, host))
					return 1
				
				if bits < 0 or bits > 32:
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, host))
					return 1
			
			else:
				stderr("%s:%d: invalid address range '%s'" % (filename, lineno, host))
				return 1
			
			if not host in new_ranges_list:
				new_ranges_list.append(host)
	
	debug('new range: %s:%s' % (alias, new_ranges_list))
	
	firewater_globals.HOSTS[alias] = new_ranges_list

	return 0


def parse_group(arr, filename, lineno):
	if len(arr) < 3:
		stderr("%s:%d: 'group' requires at least 2 arguments: the group alias and at least 1 member" % (filename, lineno))
		return 1
	
	alias = arr[1]
	
	group_list = string.join(arr[2:], ',')
	group_list = string.replace(group_list, ' ', '')
	group_list = string.replace(group_list, ',,', ',')
	group_list = string.split(group_list, ',')
	
	if alias in group_list:
		stderr("%s:%d: range %s references back to itself" % (filename, lineno, alias))
		return 1
	
	# note that group are stored in the same way as groups
	if firewater_globals.HOSTS.has_key(alias):
		stderr("%s:%d: redefinition of range or group %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_group_list = []
	while len(group_list) > 0:
		group = group_list.pop(0)
		if firewater_globals.HOSTS.has_key(group):
			group_list.extend(firewater_globals.HOSTS[group])
		else:
			# treat as IP address or fqdn
			if string.find(group, ':') > -1:
				# treat as IPv6 address
				pass
			
			elif string.find(group, '/') > -1:
				# treat as network range
				a = string.split(group, '/')
				if len(a) != 2:
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, group))
					return 1
				
				if not _is_ipv4_address(a[0]):
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, group))
					return 1
				
				try:
					bits = int(a[1])
				except ValueError:
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, group))
					return 1
				
				if bits < 0 or bits > 32:
					stderr("%s:%d: invalid address range '%s'" % (filename, lineno, group))
					return 1
			
			else:
				# treat as fqdn, so resolve the address
				addrs = firewater_resolv.resolv(group)
				if addrs == None:	# error
					stderr("%s:%d: failed to resolve '%s'" % (filename, lineno, group))
					return 1
				
				for addr in addrs:
					if not addr in new_group_list:
						new_group_list.append(addr)
				
				continue
			
			if not group in new_group_list:
				new_group_list.append(group)
	
	debug('new group: %s:%s' % (alias, new_group_list))
	
	firewater_globals.HOSTS[alias] = new_group_list
	
	return 0


def parse_serv(arr, filename, lineno):
	return parse_service(arr, filename, lineno)


def parse_service(arr, filename, lineno):
	if len(arr) < 3:
		stderr("%s:%d: '%s' requires at least 2 arguments: the service alias and at least 1 property" % (filename, lineno, arr[0]))
		return 1
	
	alias = arr[1]
	
	if firewater_globals.SERVICES.has_key(alias):
		stderr("%s:%d: redefinition of service %s" % (filename, lineno, alias))
		return 1
	
	obj = firewater_service.ServiceObject(alias)
	
	if arr[2] in ('tcp', 'udp', 'icmp', 'gre'):
		obj.proto = arr.pop(2)
	
	if len(arr) < 3:
		stderr("%s:%d: missing service or port number" % (filename, lineno))
		return 1
	
	if string.find(string.digits, arr[2][0]) > -1:
		# treat as port number or range
		if string.find(arr[2], '-') > -1:
			# treat as port range
			port_range = arr[2]
			
			port_arr = string.split(port_range, '-')
			if len(port_arr) != 2:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			try:
				obj.port = int(port_arr[0])
			except ValueError:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			try:
				obj.endport = int(port_arr[1])
			except ValueError:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			if obj.port < -1 or obj.port > 65535:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			if obj.endport < -1 or obj.endport > 65535 or obj.endport < obj.port:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
		
		elif string.find(arr[2], ':') > -1:
			# treat as port range (same code as above, split by ':') (yeah stupid, I know)
			port_range = arr[2]
			
			port_arr = string.split(port_range, ':')
			if len(port_arr) != 2:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			try:
				obj.port = int(port_arr[0])
			except ValueError:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			try:
				obj.endport = int(port_arr[1])
			except ValueError:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			if obj.port < -1 or obj.port > 65535:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
			
			if obj.endport < -1 or obj.endport > 65535 or obj.endport < obj.port:
				stderr("%s:%d: invalid port range '%s'" % (filename, lineno, port_range))
				return 1
		
		else:
			# single port number
			try:
				obj.port = int(arr[2])
			except ValueError:
				stderr("%s:%d: invalid port number '%s'" % (filename, lineno, arr[2]))
				return 1
	
	else:
		if arr[2] == alias:
			stderr("%s:%d: service %s references back to itself" % (filename, lineno))
			return -1
		
		if firewater_globals.SERVICES.has_key(arr[2]):
			obj2 = firewater_globals.SERVICES[arr[2]]
		
			# copy the other service object
			if not obj.proto:
				obj.proto = obj2.proto
			
			obj.port = obj2.port
			obj.endport = obj2.endport
			obj.iface = obj2.iface
		
		else:
			# treat as system service name
			obj.port = firewater_service.servbyname(arr[2])
			if obj.port == None:
				stderr("%s:%d: no such service '%s'" % (filename, lineno, arr[2]))
				return 1
	
	if len(arr) > 3:
		if arr[3] in ('iface', 'interface'):
			if len(arr) == 5:
				# interface-specific service
				iface = arr[4]
				if firewater_globals.INTERFACES.has_key(iface):
					obj.iface = firewater_globals.INTERFACES[iface]
				else:
					# treat as real system interface
					obj.iface = []
					obj.iface.append(arr[4])
			
			else:
				stderr("%s:%d: too many arguments to '%s'" % (filename, lineno, arr[0]))
				return 1
	
	debug('new service: %s:%s' % (alias, obj))
	
	firewater_globals.SERVICES[alias] = obj
	
	return 0


def parse_chain(arr, filename, lineno):
	if len(arr) < 2:
		stderr("%s:%d: syntax error" % (filename, lineno))
		return 1
	
	chain = arr[1]
	
	if not chain in ('incoming', 'outgoing', 'forwarding'):
		stderr("%s:%d: syntax error: unknown chain '%s'" % (filename, lineno, chain))
		return 1
	
	if len(arr) == 5:
		if arr[2] != 'default' or arr[3] != 'policy':
			stderr("%s:%d: syntax error" % (filename, lineno))
			return 1
		
		policy = arr[4]
		
		if not policy in ('allow', 'deny', 'reject', 'accept', 'drop'):
			stderr("%s:%d: syntax error: unknown policy '%s'" % (filename, lineno, policy))
			return 1
		
		# allow for common aliases to be used here
		if policy == 'accept':
			policy = 'allow'
		
		if policy == 'drop':
			policy = 'deny'
		
		# TODO emit default policy setting code
		debug('emit: %s policy %s' % (chain, policy))
	
	else:
		if len(arr) == 2:
			# change the current chain
			firewater_globals.CURRENT_CHAIN = chain
			
			debug('CURRENT_CHAIN == %s' % firewater_globals.CURRENT_CHAIN)
		
		else:
			stderr("%s:%d: syntax error" % (filename, lineno))
			return 1

	return 0


# EOB
