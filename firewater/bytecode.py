#
#   firewater/bytecode.py   WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

'''implements firewater bytecode'''

class ByteCode(object):
    '''holds the bytecode from which the output statements
    will be generated
    '''

    TYPE_RULE = 1
    TYPE_POLICY = 2
    TYPE_CHAIN = 3
    TYPE_ECHO = 4
    TYPE_VERBATIM = 5
    TYPE_COMMENT = 6
    TYPE_EXIT = 7

    TYPES = ('None', 'rule', 'policy', 'chain', 'echo', 'verbatim',
             'comment', 'exit')

    def __init__(self):
        '''initialize instance'''

        self.type = None

    def set_rule(self, filename, lineno, allow, proto, src, src_port,
                 dest, dest_port, iface):
        '''initialize as rule'''

        self.type = ByteCode.TYPE_RULE
        self.filename = filename
        self.lineno = lineno
        self.allow = allow
        self.proto = proto
        self.src = src
        self.src_port = src_port
        self.dest = dest
        self.dest_port = dest_port
        self.iface = iface

    def set_policy(self, filename, lineno, chain, policy):
        '''initialize as policy'''

        self.type = ByteCode.TYPE_POLICY
        self.filename = filename
        self.lineno = lineno
        self.chain = chain
        self.policy = policy

    def set_chain(self, filename, lineno, chain):
        '''initialize as chain'''

        self.type = ByteCode.TYPE_CHAIN
        self.filename = filename
        self.lineno = lineno
        self.chain = chain

    def set_echo(self, filename, lineno, msg):
        '''initialize as echo (print message)'''

        self.type = ByteCode.TYPE_ECHO
        self.filename = filename
        self.lineno = lineno
        self.str = msg

    def set_verbatim(self, filename, lineno, arr):
        '''initialize as verbatim block'''

        self.type = ByteCode.TYPE_VERBATIM
        self.filename = filename
        self.lineno = lineno
        self.text_array = arr[:]

    def set_comment(self, filename, lineno, comment):
        '''initialize as comment'''

        self.type = ByteCode.TYPE_COMMENT
        self.filename = filename
        self.lineno = lineno
        self.comment = comment

        if len(self.comment) > 200:
            self.comment = self.comment[:200] + " ... (long line truncated)"

    def set_exit(self, filename, lineno, exit_code):
        '''initialize as exit statement'''

        self.type = ByteCode.TYPE_EXIT
        self.filename = filename
        self.lineno = lineno
        self.exit_code = exit_code

# EOB
