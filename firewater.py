#! /usr/bin/env python
#
#	firewater.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

import sys
sys.path.append('/usr/lib/firewater')

import firewater
import firewater.globals
import firewater.parser
import firewater.bytecode

from firewater.lib import *

import os
import sys
import string
import getopt
import errno


def generate():
	'''loads plugin module and generates the rules'''
	
	# insert default 'chain: incoming' rule
	rule = firewater.bytecode.ByteCode()
	rule.set_chain('', 0, 'incoming')
	firewater.globals.BYTECODE.insert(0, rule)
	
	# load appropriate module
	module = __import__('firewater.' + firewater.globals.MODULE)
	module = getattr(module, firewater.globals.MODULE)
	
	# generate rules from bytecode
	module.begin()
	
	while True:
		if not len(firewater.globals.BYTECODE):
			break
		
		bytecode = firewater.globals.BYTECODE.pop(0)
		if bytecode == None:
			break
		
		debug('bytecode: %s' % firewater.bytecode.ByteCode.TYPES[bytecode.type])
		
		if bytecode.type == firewater.bytecode.ByteCode.TYPE_RULE:
			module.generate_rule(bytecode)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_POLICY:
			module.generate_policy(bytecode)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_CHAIN:
			module.change_chain(bytecode)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_ECHO:
			module.generate_echo(bytecode)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_VERBATIM:
			module.generate_verbatim(bytecode)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_COMMENT:
			if firewater.globals.VERBOSE:
				module.generate_comment(bytecode)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_DEFINE:
			debug('defining %s' % bytecode.definename)
			firewater.globals.DEFINES.append(bytecode.definename)
			debug('DEFINES == %s' % firewater.globals.DEFINES)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_IFDEF:
			debug('DEFINES == %s' % firewater.globals.DEFINES)
			if bytecode.definename in firewater.globals.DEFINES:
				debug('ifdef %s : match' % bytecode.definename)
			
			else:
				debug('ifdef %s : no match, skipping to next endif' % bytecode.definename)
				skip_to_next_endif(module)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_IFNDEF:
			debug('DEFINES == %s' % firewater.globals.DEFINES)
			if not bytecode.definename in firewater.globals.DEFINES:
				debug('ifndef %s : match (not defined)' % bytecode.definename)
			
			else:
				debug('ifndef %s : no match, skipping to next endif' % bytecode.definename)
				skip_to_next_endif(module)
		
		elif bytecode.type == firewater.bytecode.ByteCode.TYPE_ENDIF:
			pass
		
		else:
			raise RuntimeError, 'invalid bytecode type %d' % bytecode.type
	
	module.end()


#
#	helper func for bytecode execution ifdef/ifndef
#
def skip_to_next_endif(module):
	previous_code = None
	
	while True:
		if not len(firewater.globals.BYTECODE):
			break
		
		bytecode = firewater.globals.BYTECODE.pop(0)
		if bytecode == None:
			break
		
		debug('skipping bytecode: %s' % firewater.bytecode.ByteCode.TYPES[bytecode.type])
		
		if bytecode.type == firewater.bytecode.ByteCode.TYPE_ENDIF:
			break
		
		else:
			previous_code = bytecode
	
	# a bit hackish ... the last comment must be about 'endif'
	# and I want to have it printed in verbose mode
	if firewater.globals.VERBOSE									\
		and bytecode != None and previous_code != None				\
		and bytecode.type == firewater.bytecode.ByteCode.TYPE_ENDIF	\
		and previous_code.type == firewater.bytecode.ByteCode.TYPE_COMMENT:
		module.generate_comment(previous_code)


def usage():
	print 'usage: %s [options] <input file> [..]' % os.path.basename(sys.argv[0])
	print 'options:'
	print '  -h, --help                  Display this information'
	print '  -v, --verbose               Verbose output'
	print '  -D, --define=DEFINE         Define a symbol'
	print '      --debug                 Enable debug mode'
	print '      --version               Print version number and exit'
	print
	print 'The syntax of the input lines is described in the documentation'
	print
	print 'firewater %s by Walter de Jong <walter@heiho.net> (c) 2011' % firewater.globals.VERSION


def get_options():
	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'h?vD:',
			['help', 'verbose', 'define=', 'debug', 'version'])
	except getopt.error, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)
	
	except getopt.GetoptError, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)
	
	except:
		usage()
		sys.exit(1)
	
	for opt, arg in opts:
		if opt in ('-h', '--help', '-?'):
			usage()
			sys.exit(1)
		
		if opt in ('-v', '--verbose'):
			firewater.globals.VERBOSE = True
			debug('verbose mode')
			continue
		
		if opt in ('-D', '--define'):
			if not arg in firewater.globals.DEFINES:
				firewater.globals.DEFINES.append(arg)
			continue
		
		if opt == '--debug':
			firewater.globals.DEBUG = True
			debug('debug mode')
			continue
		
		if opt == '--version':
			print firewater.globals.VERSION
			sys.exit(0)
	
	# remaining arguments are filenames for input
	return args


def main():
	input_files = get_options()
	
	# read input: the rule set
	errors = 0
	
	if not input_files:
		errors = firewater.parser.read_input_file('/dev/stdin')
	else:
		for filename in input_files:
			errors = firewater.parser.read_input_file(filename)
	
	if errors:
		sys.exit(1)
	
	# define the name of the current output module as a 'DEFINE'
	if not firewater.globals.MODULE in firewater.globals.DEFINES:
		firewater.globals.DEFINES.insert(0, firewater.globals.MODULE)
	
	# generate output: the translated rules
	generate()
	
	sys.exit(0)


if __name__ == '__main__':
	try:
		main()
	except IOError, ioerr:
		if ioerr.errno == errno.EPIPE:		# Broken pipe
			pass
		else:
			print ioerr

	except KeyboardInterrupt:		# user pressed Ctrl-C
		pass

# EOB
