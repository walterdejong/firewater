#
#   firewater/lib.py    WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

'''utility functions'''

import firewater.globals

import sys


def stderr(line):
    '''print message on stderr'''

    sys.stderr.write(line + '\n')


def debug(line):
    '''print debug message'''

    if firewater.globals.DEBUG:
        print 'DEBUG:', line


def fatal(line):
    '''print error message and exit'''

    stderr('ERROR: ' + line)
    sys.exit(127)


def warning(line):
    '''print warning message'''

    stderr('warning: ' + line)


def error(line):
    '''print error message'''

    stderr('error: ' + line)

# EOB
