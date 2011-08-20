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

from firewater_globals import *
from firewater_lib import *

import firewater_resolv

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
			stderr('%s:%d: syntax error ; expected key/value pair' % (filename, lineno))
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
	
	if INTERFACES.has_key(alias):
		stderr("%s:%d: redefinition of interface %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_iface_list = []
	while len(iface_list) > 0:
		iface = iface_list.pop(0)
		if INTERFACES.has_key(iface):
			iface_list.extend(INTERFACES[iface])
		else:
			# treat as real system interface name
			if not iface in new_iface_list:
				new_iface_list.append(iface)
	
	INTERFACES[alias] = new_iface_list
	
	all_ifaces = INTERFACES['all']
	for iface in new_iface_list:
		if not iface in all_ifaces:
			all_ifaces.append(iface)
	
	return 0


def parse_debug(arr, filename, lineno):
	if len(arr) < 2:
		stderr("%s:%d: usage: debug interfaces|hosts" % (filename, lineno))
		return 1
	
	if arr[1] == 'interfaces':
		print 'INTERFACES ==', INTERFACES
		print
		return 0
	
	elif arr[1] == 'host' or arr[1] == 'hosts':
		print 'HOSTS ==', HOSTS
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
	
	if HOSTS.has_key(alias):
		stderr("%s:%d: redefinition of host %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_host_list = []
	while len(host_list) > 0:
		host = host_list.pop(0)
		if HOSTS.has_key(host):
			host_list.extend(HOSTS[host])
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
	
	HOSTS[alias] = new_host_list
	
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
	if HOSTS.has_key(alias):
		stderr("%s:%d: redefinition of range or host %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_ranges_list = []
	while len(ranges_list) > 0:
		# 'range' is a Python keyword ... so I use 'host' instead (confusing huh?)
		host = ranges_list.pop(0)
		if HOSTS.has_key(host):
			ranges_list.extend(HOSTS[host])
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
	
	HOSTS[alias] = new_ranges_list

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
	if HOSTS.has_key(alias):
		stderr("%s:%d: redefinition of range or group %s" % (filename, lineno, alias))
		return 1
	
	# expand the list by filling in any previously defined aliases
	new_group_list = []
	while len(group_list) > 0:
		group = group_list.pop(0)
		if HOSTS.has_key(group):
			group_list.extend(HOSTS[group])
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
	
	HOSTS[alias] = new_group_list

	return 0


# EOB
