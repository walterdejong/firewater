#
#   firewater/service.py    WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

'''implements firewater service'''

import socket

from typing import List, Optional


class ServiceObject:
    '''object respresenting a service'''

    # pylint: disable=too-few-public-methods

    def __init__(self, name: Optional[str] = None, port: Optional[int] = 0, endport: Optional[int] = 0,
                 proto: Optional[str] = None, iface: Optional[List[str]] = None) -> None:
        self.name = name
        if port is None:
            self.port = 0
        else:
            self.port = port
        if endport is None:
            self.endport = 0
        else:
            self.endport = endport  # it can be a port range
        self.proto = proto          # forced protocol
        self.iface = iface          # forced onto an interface

    def __repr__(self):
        return f'<ServiceObject: {self.name},{self.proto},{self.port},{self.endport},{self.iface}>'


def servbyname(name: str) -> int:
    '''Return service port number
    Raises KeyError if no such service
    '''

    try:
        return socket.getservbyname(name)
    except socket.error as err:
        raise KeyError(f"no such service: '{name}'") from err


# EOB
