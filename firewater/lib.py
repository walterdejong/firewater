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

import sys

import firewater.globals


def stderr(line: str) -> None:
    '''print message on stderr'''

    sys.stderr.write(line + '\n')


def debug(line: str) -> None:
    '''print debug message'''

    if firewater.globals.DEBUG:
        print('DEBUG: {}'.format(line))


def fatal(line: str) -> None:
    '''print error message and exit'''

    stderr('ERROR: ' + line)
    sys.exit(127)


def warning(line: str) -> None:
    '''print warning message'''

    stderr('warning: ' + line)


def error(line: str) -> None:
    '''print error message'''

    stderr('error: ' + line)

# EOB
