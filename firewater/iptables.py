#
#   firewater/iptables.py   WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

'''firewater output generator for iptables'''

from firewater.bytecode import ByteCode


CURRENT_CHAIN = None


def begin() -> None:
    '''output header lines'''

    print('*filter')


def end() -> None:
    '''output trailing lines'''

    print('COMMIT')


def generate_rule(bytecode: ByteCode) -> None:
    '''generate output for bytecode'''

    # pylint: disable=too-many-branches

    if not CURRENT_CHAIN:
        raise RuntimeError('CURRENT_CHAIN is not set')

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
            iface_arg = f' -i {bytecode.iface}'

        elif CURRENT_CHAIN == 'outgoing':
            iface_arg = f' -o {bytecode.iface}'

        elif CURRENT_CHAIN == 'forwarding':
            # well ... -o iface is not really supported :P
            # which means forwarding is not fully supported/implemented
            iface_arg = f' -i {bytecode.iface}'

        else:
            raise RuntimeError(f'unknown chain {CURRENT_CHAIN}')

    proto_arg = ''
    if bytecode.proto:
        proto_arg = f' -p {bytecode.proto}'

    src_port_arg = ''
    if bytecode.src_port.port > 0:
        if not proto_arg:
            raise RuntimeError('source port needs to know a protocol')

        if bytecode.src_port.endport > 0:
            src_port_arg = f' --sport {bytecode.src_port.port}:{bytecode.src_port.endport}'
        else:
            src_port_arg = f' --sport {bytecode.src_port.port}'

    dest_port_arg = ''
    if bytecode.dest_port.port > 0:
        if not proto_arg:
            raise RuntimeError('destination port needs to know a protocol')

        if bytecode.dest_port.endport > 0:
            dest_port_arg = f' --dport {bytecode.dest_port.port}:{bytecode.dest_port.endport}'
        else:
            dest_port_arg = f' --dport {bytecode.dest_port.port}'

    target_arg = None
    if bytecode.allow == 'allow':
        target_arg = 'ACCEPT'

    elif bytecode.allow == 'deny':
        target_arg = 'DROP'

    elif bytecode.allow == 'reject':
        target_arg = 'REJECT'

    else:
        raise RuntimeError(f'unknown target {bytecode.allow}')

    # output iptables rule
    print(f'-A {chain}{iface_arg}{proto_arg} -s {bytecode.src}{src_port_arg} -d {bytecode.dest}{dest_port_arg} -j {target_arg}')


def generate_policy(bytecode: ByteCode) -> None:
    '''generate policy for bytecode'''

    chain = ''
    if bytecode.chain == 'incoming':
        chain = 'INPUT'

    elif bytecode.chain == 'outgoing':
        chain = 'OUTPUT'

    elif bytecode.chain == 'forwarding':
        chain = 'FORWARD'

    else:
        raise RuntimeError(f'unknown policy chain {bytecode.chain}')

    policy = ''
    if bytecode.policy == 'allow':
        policy = 'ACCEPT'

    elif bytecode.policy == 'deny':
        policy = 'DROP'

    else:
        raise RuntimeError(f'unknown policy {bytecode.policy}')

    print(f':{chain} {policy}')


def change_chain(bytecode: ByteCode) -> None:
    '''change iptables chain'''

    global CURRENT_CHAIN                                # pylint: disable=global-statement

    CURRENT_CHAIN = bytecode.chain


def generate_echo(bytecode: ByteCode) -> None:
    '''generate print statement'''

    print(bytecode.str)


def generate_verbatim(bytecode: ByteCode) -> None:
    '''generate verbatim block'''

    for line in bytecode.text_array:
        print(line)


def generate_comment(bytecode: ByteCode) -> None:
    '''generate comment line'''

    print(f'# {bytecode.filename}:{bytecode.lineno}: {bytecode.comment}')


# EOB
