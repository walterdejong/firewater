#
#	firewater/lib.py	WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2011
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

import firewater.globals

import sys


def stderr(line):
	sys.stderr.write(line + '\n')


def debug(line):
	if firewater.globals.DEBUG:
		print 'DEBUG:', line


def fatal(line):
	stderr('ERROR: ' + line)
	sys.exit(127)


def warning(line):
	stderr('warning: ' + line)


def error(line):
	stderr('error: ' + line)


# EOB

