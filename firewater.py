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

from firewater_globals import *
from firewater_lib import *

import firewater_parser

import os
import sys
import string
import getopt
import errno


def usage():
	print 'usage: %s [options] <input file> [..]' % os.path.basename(sys.argv[0])
	print 'options:'
	print '  -h, --help                     Display this information'
	print '  -D, --debug                    Enable debug mode'
	print '      --version                  Print version number and exit'
	print
	print 'The syntax of the input lines is described in the documentation'
	print
	print 'Written by Walter de Jong <walter@heiho.net> (c) 2011'


def get_options():
	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'h?D', ['help', 'debug', 'version'])
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
		
		if opt in ('-D', '--debug'):
			DEBUG = True
			debug('debug mode')
			continue

		if opt == '--version':
			print VERSION
			sys.exit(0)
	
	# remaining arguments are filenames for input
	return args


def main():
	input_files = get_options()

	if not input_files:
		firewater_parser.read_input_file('/dev/stdin')
	else:
		for filename in input_files:
			firewater_parser.read_input_file(filename)


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
