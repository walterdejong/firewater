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

from typing import List, Optional

from firewater.service import ServiceObject


class ByteCode:
    '''holds the bytecode from which the output statements
    will be generated
    '''

    # pylint: disable=attribute-defined-outside-init

    TYPE_RULE = 1
    TYPE_POLICY = 2
    TYPE_CHAIN = 3
    TYPE_ECHO = 4
    TYPE_VERBATIM = 5
    TYPE_COMMENT = 6
    TYPE_EXIT = 7

    TYPES = ('None', 'rule', 'policy', 'chain', 'echo', 'verbatim',
             'comment', 'exit')

    def __init__(self) -> None:
        '''initialize instance'''

        self.type = None                # type: Optional[int]

    def set_rule(self, filename: str, lineno: int, allow: str, proto: Optional[str],
                 src: str, src_port: ServiceObject, dest: str, dest_port: ServiceObject,
                 iface: Optional[str]) -> None:
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

    def set_policy(self, filename: str, lineno: int, chain: str, policy: str) -> None:
        '''initialize as policy'''

        self.type = ByteCode.TYPE_POLICY
        self.filename = filename
        self.lineno = lineno
        self.chain = chain
        self.policy = policy

    def set_chain(self, filename: str, lineno: int, chain: str) -> None:
        '''initialize as chain'''

        self.type = ByteCode.TYPE_CHAIN
        self.filename = filename
        self.lineno = lineno
        self.chain = chain

    def set_echo(self, filename: str, lineno: int, msg: str) -> None:
        '''initialize as echo (print message)'''

        self.type = ByteCode.TYPE_ECHO
        self.filename = filename
        self.lineno = lineno
        self.str = msg

    def set_verbatim(self, filename: str, lineno: int, arr: List[str]) -> None:
        '''initialize as verbatim block'''

        self.type = ByteCode.TYPE_VERBATIM
        self.filename = filename
        self.lineno = lineno
        self.text_array = arr[:]

    def set_comment(self, filename: str, lineno: int, comment: str) -> None:
        '''initialize as comment'''

        self.type = ByteCode.TYPE_COMMENT
        self.filename = filename
        self.lineno = lineno
        self.comment = comment

        if len(self.comment) > 200:
            self.comment = self.comment[:200] + " ... (long line truncated)"

    def set_exit(self, filename: str, lineno: int, exit_code: int) -> None:
        '''initialize as exit statement'''

        self.type = ByteCode.TYPE_EXIT
        self.filename = filename
        self.lineno = lineno
        self.exit_code = exit_code

# EOB
