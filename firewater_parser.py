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
		stderr("%s:%d: usage: debug interfaces" % (filename, lineno))
		return 1
	
	if arr[1] == 'interfaces':
		print 'INTERFACES ==', INTERFACES
		print
		return 0
	
	stderr("%s:%d: don't know how to debug '%s'" % (filename, lineno, arr[1]))
	return 1


# keyword: group
def parse_group(arr, filename, lineno):
	if len(arr) < 3:
		stderr("%s:%d: 'group' requires at least 2 arguments: the group name and at least 1 member" % (filename, lineno))
		return 1
	
	group = arr[1]
	
	if firewater_param.GROUP_DEFS.has_key(group):
		stderr('%s:%d: redefiniton of group %s' % (filename, lineno, group))
		return 1
	
	if firewater_param.NODES.has_key(group):
		stderr('%s:%d: %s was previously defined as a node' % (filename, lineno, group))
		return 1
	
	try:
		firewater_param.GROUP_DEFS[group] = expand_grouplist(arr[2:])
	except RuntimeError, e:
		stderr('%s:%d: compound groups can not contain node names' % (filename, lineno))
		return 1
	
	return 0


# keyword: host
def parse_host(arr, filename, lineno):
	if len(arr) < 2:
		stderr("%s:%d: '%s' requires at least 1 argument: the nodename" % (filename, lineno, arr[0]))
		return 1
	
	node = arr[1]
	groups = arr[2:]
	
	if firewater_param.NODES.has_key(node):
		stderr('%s:%d: redefinition of node %s' % (filename, lineno, node))
		return 1
	
	if firewater_param.GROUP_DEFS.has_key(node):
		stderr('%s:%d: %s was previously defined as a group' % (filename, lineno, node))
		return 1
	
	#
	# node lines may end with special optional qualifiers like
	# 'interface:', 'ipaddress:', 'hostname:'
	#
	# as a consequence, group names can no longer have a colon ':' in them
	#
	while len(groups) >= 1:
		n = string.find(groups[-1], ':')
		if n < 0:
			break
		
		if n == 0:
			stderr("%s:%d: syntax error in node qualifier '%s'" % (filename, lineno, groups[-1]))
			return 1
		
		if n > 0:
			option = groups.pop()
			qualifier = option[:n]
			arg = option[n+1:]
			
			if qualifier == 'interface' or qualifier == 'ipaddress':
				if firewater_param.INTERFACES.has_key(node):
					stderr('%s:%d: redefinition of IP address for node %s' % (filename, lineno, node))
					return 1
				
				if not arg:
					stderr("%s:%d: missing argument to node qualifier '%s'" % (filename, lineno, qualifier))
					return 1
				
				firewater_param.INTERFACES[node] = arg
			
			elif qualifier == 'hostname':
				if firewater_param.HOSTNAMES.has_key(arg):
					stderr('%s:%d: hostname %s already in use for node %s' % (filename, lineno, arg, firewater_param.HOSTNAMES[arg]))
					return 1
				
				if not arg:
					stderr("%s:%d: missing argument to node qualifier 'hostname'" % (filename, lineno))
					return 1
				
				firewater_param.HOSTNAMES[arg] = node
				firewater_param.HOSTNAMES_BY_NODE[node] = arg
			
			else:
				stderr('%s:%d: unknown node qualifier %s' % (filename, lineno, qualifier))
				return 1
	
	try:
		firewater_param.NODES[node] = expand_grouplist(groups)
	except RuntimeError, e:
		stderr('%s:%d: a group list can not contain node names' % (filename, lineno))
		return 1
	
	return 0


def expand_grouplist(grouplist):
	'''expand a list of (compound) groups recursively
	Returns the expanded group list'''
	
	groups = []
	
	for elem in grouplist:
		groups.append(elem)
		
		if firewater_param.GROUP_DEFS.has_key(elem):
			compound_groups = firewater_param.GROUP_DEFS[elem]
			
			# mind that GROUP_DEFS[group] can be None
			# for any groups that have no subgroups
			if compound_groups != None:
				groups.extend(compound_groups)
		else:
			# node names are often treated in the code as groups too ...
			# but they are special groups, and can not be in a compound group just
			# to prevent odd things from happening
			if firewater_param.NODES.has_key(elem):
				raise RuntimeError, 'node %s can not be part of compound group list' % elem
			
			firewater_param.GROUP_DEFS[elem] = None
	
	# remove duplicates
	# this looks pretty lame ... but Python sets are not usable here;
	# sets mess around with the order and Python sets changed in Python 2.6
	
	expanded_grouplist = []
	for elem in groups:
		if not elem in expanded_grouplist:
			expanded_grouplist.append(elem)
	
	return expanded_grouplist


# EOB
