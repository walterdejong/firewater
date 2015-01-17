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

CURRENT_CHAIN = None


def begin():
    '''output header lines'''

    print '*filter'


def end():
    '''output trailing lines'''

    print 'COMMIT'


def generate_rule(bytecode):
    '''generate output for bytecode'''

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
            iface_arg = ' -i %s' % bytecode.iface

        elif CURRENT_CHAIN == 'outgoing':
            iface_arg = ' -o %s' % bytecode.iface

        elif CURRENT_CHAIN == 'forwarding':
            # well ... -o iface is not really supported :P
            # which means forwarding is not fully supported/implemented
            iface_arg = ' -i %s' % bytecode.iface

        else:
            raise RuntimeError('unknown chain %s' % CURRENT_CHAIN)

    proto_arg = ''
    if bytecode.proto:
        proto_arg = ' -p %s' % bytecode.proto

    src_port_arg = ''
    if bytecode.src_port.port > 0:
        if not proto_arg:
            raise RuntimeError('source port needs to know a protocol')

        if bytecode.src_port.endport > 0:
            src_port_arg = ' --sport %d:%d' % (bytecode.src_port.port,
                                               bytecode.src_port.endport)
        else:
            src_port_arg = ' --sport %d' % bytecode.src_port.port

    dest_port_arg = ''
    if bytecode.dest_port.port > 0:
        if not proto_arg:
            raise RuntimeError('destination port needs to know a protocol')

        if bytecode.dest_port.endport > 0:
            dest_port_arg = ' --dport %d:%d' % (bytecode.dest_port.port,
                                                bytecode.dest_port.endport)
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
        raise RuntimeError('unknown target %s' % bytecode.allow)

    # output iptables rule
    print '-A %s%s%s -s %s%s -d %s%s -j %s' % (chain, iface_arg, proto_arg,
        bytecode.src, src_port_arg, bytecode.dest, dest_port_arg, target_arg)


def generate_policy(bytecode):
    '''generate policy for bytecode'''

    chain = ''
    if bytecode.chain == 'incoming':
        chain = 'INPUT'

    elif bytecode.chain == 'outgoing':
        chain = 'OUTPUT'

    elif bytecode.chain == 'forwarding':
        chain = 'FORWARD'

    else:
        raise RuntimeError('unknown policy chain %s' % bytecode.chain)

    policy = ''
    if bytecode.policy == 'allow':
        policy = 'ACCEPT'

    elif bytecode.policy == 'deny':
        policy = 'DROP'

    else:
        raise RuntimeError('unknown policy %s' % bytecode.policy)

    print ':%s %s' % (chain, policy)


def change_chain(bytecode):
    '''change iptables chain'''

    global CURRENT_CHAIN

    CURRENT_CHAIN = bytecode.chain


def generate_echo(bytecode):
    '''generate print statement'''

    print bytecode.str


def generate_verbatim(bytecode):
    '''generate verbatim block'''

    for line in bytecode.text_array:
        print line


def generate_comment(bytecode):
    '''generate comment line'''

    print '# %s:%d: %s' % (bytecode.filename, bytecode.lineno,
                           bytecode.comment)

# EOB
