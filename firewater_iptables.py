#! /usr/bin/env python
#
#	firewater_iptables.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

from firewater_lib import *

import firewater_bytecode


CURRENT_CHAIN = None


def begin():
	debug('firewater_iptables.begin()')

	print '*filter'


def generate(bytecode_array):
	debug('firewater_iptables.generate()')
	
	for bytecode in bytecode_array:
		if bytecode.type == firewater_bytecode.ByteCode.TYPE_RULE:
			_generate_rule(bytecode)
		
		elif bytecode.type == firewater_bytecode.ByteCode.TYPE_POLICY:
			_generate_policy(bytecode)
		
		elif bytecode.type == firewater_bytecode.ByteCode.TYPE_CHAIN:
			_change_chain(bytecode)
		
		elif bytecode.type == firewater_bytecode.ByteCode.TYPE_ECHO:
			_generate_echo(bytecode)
		
		elif bytecode.type == firewater_bytecode.ByteCode.TYPE_VERBATIM:
			_generate_verbatim(bytecode)
		
		else:
			raise RuntimeError, 'invalid bytecode type %d' % bytecode.type


def end():
	debug('firewater_iptables.end()')

	print 'COMMIT'


def _generate_rule(bytecode):
	if not CURRENT_CHAIN:
		raise RuntimeError, 'CURRENT_CHAIN is not set'
	
	chain = ''
	if CURRENT_CHAIN == 'incoming':
		chain = 'INPUT'
	
	elif CURRENT_CHAIN == 'outgoing':
		chain = 'OUTPUT'
	
	elif CURRENT_CHAIN == 'forwarding':
		chain = 'FORWARD'
	
	iface_arg = ''
	if bytecode.iface:
		if CURRENT_CHAIN == 'incoming':
			iface_arg = ' -i %s' % bytecode.iface
		
		elif CURRENT_CHAIN == 'outgoing':
			iface_arg = ' -o %s' % bytecode.iface
		
		elif CURRENT_CHAIN == 'forwarding':
			# well ... -o iface is not really supported :P
			# which means forwarding is not fully supported/implemented
			iface_arg = ' -i %s' % bytecode.iface
		
		else:
			raise RuntimeError, 'unknown chain %s' % CURRENT_CHAIN
	
	proto_arg = ''
	if bytecode.proto:
		proto_arg = ' -p %s' % bytecode.proto
	
	src_port_arg = ''
	if bytecode.src_port.port > 0:
		if bytecode.src_port.endport > 0:
			src_port_arg = ' --sport %d:%d' % (bytecode.src_port.port, bytecode.src_port.endport)
		else:
			src_port_arg = ' --sport %d' % bytecode.src_port.port
	
	dest_port_arg = ''
	if bytecode.dest_port.port > 0:
		if bytecode.dest_port.endport > 0:
			dest_port_arg = ' --dport %d:%d' % (bytecode.dest_port.port, bytecode.dest_port.endport)
		else:
			dest_port_arg = ' --dport %d' % bytecode.dest_port.port
	
	target_arg = None
	if bytecode.allow == 'allow':
		target_arg = 'ACCEPT'
	
	elif bytecode.allow == 'deny':
		target_arg = 'DROP'
	
	elif bytecode.allow == 'reject':
		target_arg = 'REJECT'
	
	else:
		raise RuntimeError, 'unknown target %s' % bytecode.allow
	
	# output iptables rule
	print '-A %s%s%s -s %s%s -d %s%s -j %s' % (chain, iface_arg, proto_arg,
		bytecode.src, src_port_arg, bytecode.dest, dest_port_arg, target_arg)


def _generate_policy(bytecode):
	chain = ''
	if bytecode.chain == 'incoming':
		chain = 'INPUT'
	
	elif bytecode.chain == 'outgoing':
		chain = 'OUTPUT'
	
	elif bytecode.chain == 'forwarding':
		chain = 'FORWARD'
	
	else:
		raise RuntimeError, 'unknown policy chain %s' % bytecode.chain
	
	policy = ''
	if bytecode.policy == 'allow':
		policy = 'ACCEPT'
	
	elif bytecode.policy == 'deny':
		policy = 'DROP'
	
	elif bytecode.policy == 'reject':
		policy = 'REJECT'
	
	else:
		raise RuntimeError, 'unknown policy %s' % bytecode.policy
	
	# Note: this also resets the counters on the chain
	# (does anyone care?)
	print ':%s %s [0:0]' % (chain, policy)


def _change_chain(bytecode):
	global CURRENT_CHAIN
	
	CURRENT_CHAIN = bytecode.chain


def _generate_echo(bytecode):
	print bytecode.str


def _generate_verbatim(bytecode):
	for line in bytecode.text_array:
		print line


# EOB
