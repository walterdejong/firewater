#
#   firewater/parser.py WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2003-2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

'''input parser code'''

#
# Note: this is a hardcoded parser
# To make a new keyword for the input file, simply define a
# Parser method like: def parse_xxx(self, arr, filename, lineno):
# and it will just work (magic trick with getattr(self, functionname))
#

import re

from typing import List, Optional, IO

import firewater.globals
import firewater.resolv
import firewater.service
import firewater.bytecode

from firewater.lib import debug, stderr


class ParseError(Exception):
    '''error message class for parse errors'''


class Parser:
    '''class that parses an input file'''

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-public-methods
    # pylint: disable=missing-function-docstring
    # pylint: disable=raise-missing-from

    def __init__(self) -> None:
        '''initialize instance'''

        self.filename = None            # type: Optional[str]
        self.file = None                # type: Optional[IO]
        self.lineno = 0
        self.full_line = None           # type: Optional[str]
        self.line = None                # type: Optional[str]
        self.comment = None             # type: Optional[str]
        self.arr = None                 # type: Optional[List[str]]
        self.keyword = None             # type: Optional[str]
        self.errors = 0
        self.in_verbatim = False
        self.verbatim_text = []         # type: List[str]
        self.ifdef_stack = []           # type: List[bool]
        self.else_stack = []            # type: List[bool]

    def __repr__(self) -> str:
        '''prints filename + line number'''

        return f'{self.filename}:{self.lineno}'

    def open(self, filename: str) -> None:
        '''open an input file

        May raise OSError
        '''

        self.filename = filename
        self.lineno = 0
        self.verbatim_text = []

        # is the ifdef true? may we execute statements?
        self.ifdef_stack = [True, ]

        # can we have an 'else' statement now?
        self.else_stack = [False, ]

        # finally, open the file
        # This may raise an OSError exception
        self.file = open(self.filename, encoding='utf-8')           # pylint: disable=consider-using-with

    def close(self) -> None:
        '''close input file'''

        if self.file is not None:
            self.file.close()
            self.file = None

        if self.in_verbatim:
            stderr(str(ParseError(f"{self}: missing 'end verbatim' statement")))

        self.lineno = 0
        self.full_line = None
        self.line = None
        self.comment = None
        self.arr = None
        self.keyword = None
        self.in_verbatim = False
        self.verbatim_text = []
        self.ifdef_stack = []
        self.else_stack = []

    def getline(self) -> bool:
        '''read statement from input file
        Upon return, self.keyword should be set, as well as other members
        Returns True when OK, False on EOF
        '''

        self.full_line = None
        self.line = ''
        self.comment = None
        self.arr = None
        self.keyword = None

        while True:
            # read lines from the input file
            # variable tmp_line is used to be able to
            # do multi-line reads (backslash terminated)
            assert self.file is not None                    # this helps mypy
            tmp_line = self.file.readline()
            if not tmp_line:
                return False

            self.lineno += 1

            if self.in_verbatim:
                # copy verbatim until the statement 'end verbatim'
                # is reached
                verbatim_line = tmp_line.strip()
                arr = verbatim_line.lower().split()
                # it is tested with an array so that both spaces
                # and tabs work
                # note that this shadows the 'end' keyword, but
                # only when in verbatim mode
                if not (len(arr) == 2 and arr[0] == 'end' and arr[1] == 'verbatim'):
                    debug(f'verbatim line == [{verbatim_line}]')
                    self.verbatim_text.append(verbatim_line)
                    continue

            n = tmp_line.find('#')
            if n >= 0:
                self.comment = '    ' + tmp_line[n:].strip()
                tmp_line = tmp_line[:n]     # strip comment
            else:
                self.comment = ''

            tmp_line = tmp_line.strip()
            if not tmp_line:
                continue

            assert self.line is not None                                    # this helps mypy
            if tmp_line[-1] == '\\':
                tmp_line = tmp_line[:-1].strip()
                self.line = self.line + ' ' + tmp_line
                continue

            self.line = self.line + ' ' + tmp_line

            assert self.line is not None                                    # this helps mypy
            assert self.comment is not None                                 # this helps mypy

            self.full_line = self.line + self.comment
            self.arr = self.line.split()
            self.keyword = self.arr[0].lower()
            break

        return True

    def interpret(self) -> int:
        '''interpret a line (first call Parser.getline())
        Returns 0 on success, 1 on error
        '''

        if not self.keyword:
            stderr(f'{self}: no keyword set; invalid parser state')
            self.errors += 1
            return 1

        if not self.ifdef_stack[0]:
            if self.keyword not in ('ifdef', 'ifndef', 'else', 'endif'):
                debug(f"{self}: skipping {self.keyword}")
                return 0

        # get the parser function
        try:
            func = getattr(self, f'parse_{self.keyword}')
        except AttributeError:
            stderr(f"{self}: unknown keyword '{self.keyword}'")
            self.errors += 1
            return 1

        try:
            func()
        except ParseError as parse_error:
            stderr(str(parse_error))
            self.errors += 1
            return 1

        return 0

    def insert_comment_line(self) -> None:
        '''insert the current line into bytecode as comment
        (this will be displayed in verbose mode)
        '''

        if self.ifdef_stack[0] or self.keyword in ('ifdef', 'ifndef', 'else', 'endif'):
            bytecode = firewater.bytecode.ByteCode()
            assert self.filename is not None
            assert self.full_line is not None
            bytecode.set_comment(self.filename, self.lineno, self.full_line)
            firewater.globals.BYTECODE.append(bytecode)

    @staticmethod
    def missing_comma(a_list: List[str]) -> Optional[str]:
        '''lists must be comma-separated, so
        if this function returns not None, then
        it's a syntax error: missing comma after element
        '''

        for elem in a_list:
            arr = elem.split()
            if len(arr) > 1:
                return arr[0]

        return None

    ### parser keywords ###

    def parse_include(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) <= 1:
            raise ParseError(f"{self}: 'include' requires a filename argument")

        include_file = ' '.join(arr[1:])

        debug(f'include {include_file}')

        try:
            # recursively read the given parse file
            if read_input_file(include_file) > 0:
                raise ParseError(f"{self}: error in included file {include_file}")

        except OSError as err:
            raise ParseError(f"{self}: failed to read file '{include_file}'") from err

    def parse_iface(self) -> None:
        self.parse_interface()

    def parse_interface(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) < 3:
            raise ParseError(f"{self}: '{self.keyword}' requires at least 2 arguments: "
                             "the interface alias and the real interface name")

        alias = arr[1]
        if alias == 'any':
            raise ParseError(f"{self}: 'any' is a reserved word")

        iface_list = ' '.join(arr[2:]).split(',')

        elem = self.missing_comma(iface_list)
        if elem is not None:
            raise ParseError(f"{self}: missing comma after '{elem}'")

        if alias in iface_list:
            raise ParseError("{self}: interface {alias} references back to itself")

        if alias in firewater.globals.INTERFACES:
            raise ParseError(f"{self}: redefinition of interface {alias}")

        # expand the list by filling in any previously defined aliases
        new_iface_list = []
        while len(iface_list) > 0:
            iface = iface_list.pop(0)
            if iface in firewater.globals.INTERFACES:
                iface_list.extend(firewater.globals.INTERFACES[iface])
            else:
                # treat as real system interface name
                if iface not in new_iface_list:
                    new_iface_list.append(iface)

        debug(f'new interface: {alias}:{new_iface_list}')

        firewater.globals.INTERFACES[alias] = new_iface_list

        all_ifaces = firewater.globals.INTERFACES['all']
        for iface in new_iface_list:
            if iface not in all_ifaces:
                all_ifaces.append(iface)

    def parse_echo(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) <= 1:
            msg = ''
        else:
            msg = ' '.join(arr[1:])

        bytecode = firewater.bytecode.ByteCode()
        assert self.filename is not None
        bytecode.set_echo(self.filename, self.lineno, msg)
        firewater.globals.BYTECODE.append(bytecode)

    def parse_host(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) < 3:
            raise ParseError(f"{self}: 'host' requires at least 2 arguments: "
                             "the host alias and the IP address or fqdn")

        alias = arr[1]
        if alias == 'any':
            raise ParseError(f"{self}: 'any' is a reserved word")

        host_list = ' '.join(arr[2:]).replace(' ', '').replace(',,', ',').split(',')

        elem = self.missing_comma(host_list)
        if elem is not None:
            raise ParseError(f"{self}: missing comma after '{elem}'")

        if alias in host_list:
            raise ParseError(f"{self}: host {alias} references back to itself")

        if alias in firewater.globals.HOSTS:
            raise ParseError(f"{self}: redefinition of host {alias}")

        # expand the list by filling in any previously defined aliases
        new_host_list = []
        while len(host_list) > 0:
            host = host_list.pop(0)
            try:
                host_list.extend(firewater.globals.HOSTS[host])
            except KeyError:
                # treat as IP address or fqdn
                if host.find(':') > -1:
                    # treat as IPv6 address
                    pass

                elif host.find('/') > -1:
                    # treat as network range
                    a = host.split('/')
                    if len(a) != 2:
                        raise ParseError(f"{self}: invalid host address '{host}'")

                    if not _is_ipv4_address(a[0]):
                        raise ParseError(f"{self}: invalid host address '{host}'")

                    if a[1] != '32':
                        raise ParseError(f"{self}: invalid host address '{host}'")

                elif _is_ipv4_address(host):
                    # treat as IPv4 address
                    pass

                else:
                    # treat as fqdn, so resolve the address
                    try:
                        addrs = firewater.resolv.resolv(host)
                    except KeyError as err:
                        raise ParseError(f"{self}: failed to resolve '{host}'") from err

                    for addr in addrs:
                        if addr not in new_host_list:
                            new_host_list.append(addr)

                    continue

                if host not in new_host_list:
                    new_host_list.append(host)

        debug(f'new host: {alias}:{new_host_list}')
        firewater.globals.HOSTS[alias] = new_host_list

    def parse_network(self) -> None:
        self.parse_range()

    def parse_range(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) < 3:
            raise ParseError(f"{self}: '{arr[0]}' requires at least 2 arguments: "
                             "the range alias and the address range")

        alias = arr[1]
        if alias == 'any':
            raise ParseError(f"{self}: 'any' is a reserved word")

        ranges_list = ' '.join(arr[2:]).replace(' ', '').replace(',,', ',').split(',')

        elem = self.missing_comma(ranges_list)
        if elem is not None:
            raise ParseError(f"{self}: missing comma after '{elem}'")

        if alias in ranges_list:
            raise ParseError(f"{self}: {arr[0]} {alias} references back to itself")

        # note that ranges are stored in the same way as hosts
        if alias in firewater.globals.HOSTS:
            raise ParseError(f"{self}: redefinition of {arr[0]} or host {alias}")

        # expand the list by filling in any previously defined aliases
        new_ranges_list = []
        while len(ranges_list) > 0:
            # 'range' is a Python keyword ...
            # so I use 'host' instead (confusing huh?)
            host = ranges_list.pop(0)
            try:
                ranges_list.extend(firewater.globals.HOSTS[host])
            except KeyError:
                # treat as IP address or fqdn
                if host.find(':') > -1:
                    # treat as IPv6 address
                    pass

                elif host.find('/') > -1:
                    # treat as network range
                    a = host.split('/')
                    if len(a) != 2:
                        raise ParseError(f"{self}: invalid address range '{host}'")

                    if not _is_ipv4_address(a[0]):
                        raise ParseError(f"{self}: invalid address range '{host}'")

                    try:
                        bits = int(a[1])
                    except ValueError as err:
                        raise ParseError(f"{self}: invalid address range '{host}'") from err

                    if bits < 0 or bits > 32:
                        raise ParseError(f"{self}: invalid address range '{host}'")

                else:
                    raise ParseError(f"{self}: invalid address range '{host}'")

                if host not in new_ranges_list:
                    new_ranges_list.append(host)

        debug(f'new {arr[0]}: {alias}:{new_ranges_list}')
        firewater.globals.HOSTS[alias] = new_ranges_list

    def parse_group(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) < 3:
            raise ParseError(f"{self}: 'group' requires at least 2 arguments: "
                             "the group alias and at least 1 member")

        alias = arr[1]
        if alias == 'any':
            raise ParseError(f"{self}: 'any' is a reserved word")

        group_list = ','.join(arr[2:]).replace(' ', '').replace(',,', ',').split(',')

        elem = self.missing_comma(group_list)
        if elem is not None:
            raise ParseError(f"{self}: missing comma after '{elem}'")

        if alias in group_list:
            raise ParseError(f"{self}: range {alias} references back to itself")

        # note that group are stored in the same way as groups
        if alias in firewater.globals.HOSTS:
            raise ParseError(f"{self}: redefinition of range or group {alias}")

        # expand the list by filling in any previously defined aliases
        new_group_list = []
        while len(group_list) > 0:
            group = group_list.pop(0)
            try:
                group_list.extend(firewater.globals.HOSTS[group])
            except KeyError:
                # treat as IP address or fqdn
                if group.find(':') > -1:
                    # treat as IPv6 address
                    pass

                elif group.find('/') > -1:
                    # treat as network range
                    a = group.split('/')
                    if len(a) != 2:
                        raise ParseError(f"{self}: invalid address range '{group}'")

                    if not _is_ipv4_address(a[0]):
                        raise ParseError(f"{self}: invalid address range '{group}'")

                    try:
                        bits = int(a[1])
                    except ValueError:
                        raise ParseError(f"{self}: invalid address range '{group}'")

                    if bits < 0 or bits > 32:
                        raise ParseError(f"{self}: invalid address range '{group}'")

                else:
                    # treat as fqdn, so resolve the address
                    try:
                        addrs = firewater.resolv.resolv(group)
                    except KeyError as err:
                        raise ParseError(f"{self}: failed to resolve '{group}'") from err

                    for addr in addrs:
                        if addr not in new_group_list:
                            new_group_list.append(addr)

                    continue

                if group not in new_group_list:
                    new_group_list.append(group)

        debug(f'new group: {alias}:{new_group_list}')

        firewater.globals.HOSTS[alias] = new_group_list

    def parse_serv(self) -> None:
        return self.parse_service()

    REGEX_NUMERIC = re.compile(r'(\d+)$')
    REGEX_PORT_RANGE = re.compile(r'(\d+)[:-](\d+)$')

    def parse_service(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) < 3:
            raise ParseError("f{self}: '{arr[0]}' requires at least 2 arguments: "
                             "the service alias and at least 1 property")

        alias = arr[1]
        if alias == 'any':
            raise ParseError(f"{self}: 'any' is a reserved word")

        if alias in firewater.globals.SERVICES:
            raise ParseError(f"{self}: redefinition of service {alias}")

        obj = firewater.service.ServiceObject(alias)

        if arr[2] in firewater.globals.KNOWN_PROTOCOLS:
            obj.proto = arr.pop(2)

        if len(arr) < 3:
            raise ParseError(f"{self}: missing service or port number")

        # parse port range or number, or alias, or service name
        m = Parser.REGEX_PORT_RANGE.match(arr[2])
        if m is not None:
            # it's a port range
            port_range = arr[2]
            obj.port = int(m.groups()[0])
            if obj.port < 0 or obj.port > 65535:
                raise ParseError(f"{self}: invalid port range '{port_range}'")

            obj.endport = int(m.groups()[1])
            if obj.endport < 0 or obj.endport > 65535:
                raise ParseError(f"{self}: invalid port range '{port_range}'")
        else:
            m = Parser.REGEX_NUMERIC.match(arr[2])
            if m is not None:
                # it's a single port number
                obj.port = int(arr[2])
                if obj.port < 0 or obj.port > 65535:
                    raise ParseError(f"{self}: invalid port number '{obj.port}'")
            else:
                # it's a string
                if arr[2] == alias:
                    raise ParseError(f"{self}: service {arr[2]} references back to itself")

                if arr[2] in firewater.globals.SERVICES:
                    obj2 = firewater.globals.SERVICES[arr[2]]

                    # copy the other service object
                    if not obj.proto:
                        obj.proto = obj2.proto

                    obj.port = obj2.port
                    obj.endport = obj2.endport
                    obj.iface = obj2.iface
                else:
                    # treat as system service name
                    try:
                        obj.port = firewater.service.servbyname(arr[2])
                    except KeyError as err:
                        raise ParseError(f"{self}: no such service '{arr[2]}'") from err

        if len(arr) > 3:
            if arr[3] in ('iface', 'interface'):
                if len(arr) == 5:
                    # interface-specific service
                    iface = arr[4]
                    try:
                        obj.iface = firewater.globals.INTERFACES[iface]
                    except KeyError:
                        # treat as real system interface
                        obj.iface = []
                        obj.iface.append(arr[4])

                else:
                    raise ParseError(f"{self}: too many arguments to '{arr[0]}'")

        debug(f'new service: {alias}:{obj}')
        firewater.globals.SERVICES[alias] = obj

    def parse_chain(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) < 2:
            raise ParseError(f"{self}: syntax error")

        chain = arr[1]

        if chain not in ('incoming', 'outgoing', 'forwarding'):
            raise ParseError(f"{self}: syntax error: unknown chain '{chain}'")

        if len(arr) == 5:
            if arr[2] != 'default' or arr[3] != 'policy':
                raise ParseError(f"{self}: syntax error")

            policy = arr[4]

            debug(f'policy == {policy}')

            if policy not in ('allow', 'deny', 'accept', 'drop'):
                raise ParseError(f"{self}: syntax error: unknown policy '{policy}'")

            # allow for common aliases to be used here
            if policy == 'accept':
                policy = 'allow'

            if policy == 'drop':
                policy = 'deny'

            debug(f'set chain {chain} policy {policy}')

            # emit default policy setting code
            bytecode = firewater.bytecode.ByteCode()
            assert self.filename is not None
            assert chain is not None
            assert policy is not None
            bytecode.set_policy(self.filename, self.lineno, chain, policy)
            firewater.globals.BYTECODE.append(bytecode)

        else:
            if len(arr) == 2:
                # change the current chain
                debug(f'set current chain {chain}')

                bytecode = firewater.bytecode.ByteCode()
                assert self.filename is not None
                assert chain is not None
                bytecode.set_chain(self.filename, self.lineno, chain)
                firewater.globals.BYTECODE.append(bytecode)

            else:
                raise ParseError(f"{self}: syntax error")

    def _parse_rule(self) -> None:
        '''parse a rule

        rule syntax:

        allow|deny|reject [<proto>] [from <source> [port <service>]] \
        [to <dest> [port <service>]] \
        [on [interface|iface] <iface> [interface]]
        '''

        assert self.arr is not None
        arr = self.arr
        allow = arr.pop(0)

        if len(arr) < 1:
            raise ParseError(f"{self}: syntax error, premature end of line")

        proto = None
        if arr[0] in firewater.globals.KNOWN_PROTOCOLS:
            proto = arr.pop(0)

        if len(arr) <= 1:
            raise ParseError(f"{self}: syntax error, premature end of line")

        # the line can be parsed using tokens

        source_addr = None
        source_port = None
        dest_addr = None
        dest_port = None
        interface = None

        while len(arr) > 0:
            token = arr.pop(0)

            if len(arr) < 1:
                raise ParseError(f"{self}: syntax error, premature end of line")

            if token == 'from':
                if source_addr is not None:
                    raise ParseError(f"{self}: syntax error ('from' is used multiple times)")

                source_addr = arr.pop(0)

                if len(arr) > 0:
                    # check for source port
                    if arr[0] == 'port':
                        arr.pop(0)

                        if len(arr) < 1:
                            raise ParseError(f"{self}: syntax error, premature end of line")

                        source_port = arr.pop(0)

                continue

            if token == 'to':
                if dest_addr is not None:
                    raise ParseError(f"{self}: syntax error ('to' is used multiple times)")

                dest_addr = arr.pop(0)

                if len(arr) > 0:
                    # check for dest port
                    if arr[0] == 'port':
                        arr.pop(0)

                        if len(arr) < 1:
                            raise ParseError(f"{self}: syntax error, premature end of line")

                        dest_port = arr.pop(0)

                continue

            if token == 'on':
                if interface is not None:
                    raise ParseError(f"{self}: syntax error ('on' is used multiple times)")

                if arr[0] in ('interface', 'iface'):
                    arr.pop(0)

                    if len(arr) < 1:
                        raise ParseError(f"{self}: syntax error, premature end of line")

                interface = arr.pop(0)

                if len(arr) > 0 and arr[0] in ('interface', 'iface'):
                    arr.pop(0)

                continue

            raise ParseError(f"{self}: syntax error, unknown token '{token}'")

        debug('rule {')
        debug(f'  {allow} proto {proto}')
        debug(f'  source ({source_addr}, {source_port})')
        debug(f'  dest   ({dest_addr}, {dest_port})')
        debug(f'  iface   {interface}')
        debug('}')

        sources = self._parse_rule_address(source_addr)
        source_svc = self._parse_rule_service(source_port)
        destinations = self._parse_rule_address(dest_addr)
        dest_svc = self._parse_rule_service(dest_port)
        ifaces = self._parse_rule_interfaces(interface)

        debug('rule got {')
        debug('  sources: ' + str(sources))
        debug('  port: ' + str(source_svc))
        debug('  destinations: ' + str(destinations))
        debug('  port: ' + str(dest_svc))
        debug('  ifaces: ' + str(ifaces))
        debug('}')

        if not proto and (source_svc.port > 0 or dest_svc.port > 0):
            if source_svc.port > 0 and source_svc.proto:
                proto = source_svc.proto

            if dest_svc.port > 0 and dest_svc.proto:
                proto = dest_svc.proto

            if not proto:
                raise ParseError(f"{self}: missing protocol")

        # save the rule in globals.BYTECODE[]
        # the output statements are generated later,
        # if there were no parse errors

        assert self.filename is not None

        for src in sources:
            for dest in destinations:
                if not ifaces:
                    debug(f'{self}: {allow} {proto} {src} eq {source_port} {dest} eq {dest_port}')
                    bytecode = firewater.bytecode.ByteCode()
                    bytecode.set_rule(self.filename, self.lineno, allow,
                                      proto, src, source_svc,
                                      dest, dest_svc, None)
                    firewater.globals.BYTECODE.append(bytecode)
                else:
                    for iface in ifaces:
                        debug(f'{self}: {allow} {proto} {src} eq {source_port} {dest} eq {dest_port} on {iface}')
                        bytecode = firewater.bytecode.ByteCode()
                        bytecode.set_rule(self.filename, self.lineno, allow,
                                          proto, src, source_svc,
                                          dest, dest_svc, iface)
                        firewater.globals.BYTECODE.append(bytecode)

    def _parse_rule_service(self, service: Optional[str]) -> firewater.service.ServiceObject:
        '''returns ServiceObject for service'''

        if not service or service == 'any':
            return firewater.service.ServiceObject()

        # FIXME use regexp for this sort of thing
        if '0123456789'.find(service[0]) > -1:
            # numeric service given
            try:
                service_port = int(service)
            except ValueError:
                raise ParseError(f"{self}: syntax error in number '{service}'")

            return firewater.service.ServiceObject(service, service_port)

        if service in firewater.globals.SERVICES:
            # previously defined service
            return firewater.globals.SERVICES[service]

        # system service
        try:
            service_port = firewater.service.servbyname(service)
        except KeyError as err:
            raise ParseError(f"{self}: unknown service '{service}'") from err

        return firewater.service.ServiceObject(service, service_port)

    def _parse_rule_address(self, address: Optional[str]) -> List[str]:
        '''returns list of addresses'''

        address_list = []

        if not address or address == 'any':
            address_list.append('0.0.0.0/0')
            return address_list

        if address in firewater.globals.HOSTS:
            address_list.extend(firewater.globals.HOSTS[address])
            return address_list

        # treat as IP address or fqdn
        if address.find(':') > -1:
            # treat as IPv6 address
            address_list.append(address)
            return address_list

        if address.find('/') > -1:
            # treat as network range
            a = address.split('/')
            if len(a) != 2:
                raise ParseError(f"{self}: invalid address range '{address}'")

            if not _is_ipv4_address(a[0]):
                raise ParseError(f"{self}: invalid address range '{address}'")

            try:
                bits = int(a[1])
            except ValueError:
                raise ParseError(f"{self}: invalid address range '{address}'")

            if bits < 0 or bits > 32:
                raise ParseError(f"{self}: invalid address range '{address}'")

            address_list.append(address)
            return address_list

        if _is_ipv4_address(address):
            address_list.append(address)
            return address_list

        # treat as fqdn
        try:
            address_list = firewater.resolv.resolv(address)
        except KeyError as err:
            raise ParseError(f"{self}: failed to resolve '{address}'") from err

        return address_list

    @staticmethod
    def _parse_rule_interfaces(interface: Optional[str]) -> List[str]:
        iface_list = []                 # type: List[str]

        if not interface or interface == 'any':
            return iface_list

        if interface in firewater.globals.INTERFACES:
            iface_list.extend(firewater.globals.INTERFACES[interface])
            return iface_list

        iface_list.append(interface)
        return iface_list

    def parse_allow(self) -> None:
        self._parse_rule()

    def parse_deny(self) -> None:
        self._parse_rule()

    def parse_reject(self) -> None:
        self._parse_rule()

    def parse_verbatim(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) > 1:
            raise ParseError(f"{self}: syntax error, 'verbatim' does not take any arguments")

        debug('in verbatim')

        self.in_verbatim = True
        self.verbatim_text = []

    def parse_end(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) > 2:
            raise ParseError(f"{self}: syntax error, 'end' takes only one argument")

        if arr[1] == 'verbatim':
            if not self.in_verbatim:
                raise ParseError(f"{self}: 'end' can not be used here")

            debug('end verbatim')

            self.in_verbatim = False

            bytecode_end_verbatim = firewater.globals.BYTECODE.pop()

            bytecode = firewater.bytecode.ByteCode()
            assert self.filename is not None
            bytecode.set_verbatim(self.filename, self.lineno, self.verbatim_text)
            firewater.globals.BYTECODE.append(bytecode)

            firewater.globals.BYTECODE.append(bytecode_end_verbatim)

        else:
            raise ParseError(f"{self}: unknown argument '{arr[1]}' to 'end'")

    def parse_define(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) != 2:
            raise ParseError(f"{self}: syntax error, 'define' takes only one argument: a symbol to define")

        debug(f'parser: define "{arr[1]}"')
        firewater.globals.DEFINES.append(arr[1])

    def parse_ifdef(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) != 2:
            raise ParseError(f"{self}: syntax error, 'ifdef' takes only one argument: a defined symbol")

        if self.ifdef_stack[0]:
            self.ifdef_stack.insert(0, arr[1] in firewater.globals.DEFINES)
        else:
            self.ifdef_stack.insert(0, False)

        self.else_stack.insert(0, True)

    def parse_ifndef(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) != 2:
            raise ParseError(f"{self}: syntax error, 'ifdef' takes only one argument: a defined symbol")

        if self.ifdef_stack[0]:
            self.ifdef_stack.insert(0,
                                    not arr[1] in firewater.globals.DEFINES)
        else:
            self.ifdef_stack.insert(0, False)

        self.else_stack.insert(0, True)

    def parse_else(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) > 1:
            raise ParseError(f"{self}: syntax error, 'else' takes no arguments")

        if len(self.ifdef_stack) <= 1 or not self.else_stack[0]:
            raise ParseError(f"{self}: error, 'else' without ifdef or ifndef")

        v = self.ifdef_stack.pop(0)
        if self.ifdef_stack[0]:
            self.ifdef_stack.insert(0, not v)
        else:
            self.ifdef_stack.insert(0, False)

        self.else_stack[0] = False

    def parse_endif(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) > 1:
            raise ParseError(f"{self}: syntax error, 'endif' takes no arguments")

        if len(self.ifdef_stack) <= 1:
            raise ParseError(f"{self}: error, 'endif' without ifdef or ifndef")

        self.ifdef_stack.pop(0)
        self.else_stack.pop(0)

    def parse_exit(self) -> None:
        assert self.arr is not None
        arr = self.arr
        if len(arr) > 2:
            raise ParseError(f"{self}: syntax error, too many arguments to 'exit'")

        exit_code = 0

        if len(arr) == 2:
            try:
                exit_code = int(arr[1])
            except ValueError:
                raise ParseError(f"{self}: syntax error, 'exit' may take an integer argument")

        bytecode = firewater.bytecode.ByteCode()
        assert self.filename is not None
        bytecode.set_exit(self.filename, self.lineno, exit_code)
        firewater.globals.BYTECODE.append(bytecode)


def _is_ipv4_address(addr: str) -> bool:
    '''returns True if addr looks like an IPv4 address
    or False if not
    '''

    arr = addr.split('.')
    if not arr:
        return False

    if len(arr) != 4:
        return False

    for i in range(0, 4):
        try:
            n = int(arr[i])
        except ValueError:
            return False

        if n < 0 or n > 255:
            return False

    return True


def read_input_file(filename: str) -> int:
    '''read a (included) input file
    Returns 0 on success, or error count on errors
    '''

    errors = 0

    parser = Parser()
    try:
        parser.open(filename)
    except OSError as err:
        stderr(f'failed to open {filename}: {err.strerror}')
        return 1

    while parser.getline():
        parser.insert_comment_line()
        parser.interpret()

    if len(parser.ifdef_stack) > 1:
        stderr(str(ParseError(f"{parser}: missing 'endif' statement")))
        errors += 1

    parser.close()
    errors = errors + parser.errors

    debug(f'errors == {errors}')
    return errors

# EOB
