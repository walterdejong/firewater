#
#   firewater/resolv.py WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.
#

'''name resolving code'''

import socket

from typing import Dict, List


CACHE = {}                              # type: Dict[str,List[str]]
CACHE6 = {}                             # type: Dict[str,List[str]]


def resolv(name: str) -> List[str]:
    '''Returns list of IPv4 addresses for name
    Raises KeyError on error
    '''

    if name in CACHE:
        return CACHE[name]

    try:
        addr_arr = socket.getaddrinfo(name, 0, socket.AF_UNSPEC)
    except socket.gaierror as err:
        raise KeyError(f"error resolving {name}") from err

    addrs = []
    addrs6 = []
    for addr in addr_arr:
        ipaddr = addr[4][0]

        if ipaddr.find(':') > -1:
            # treat as IPv6 address
            if ipaddr not in addrs6:
                addrs6.append(ipaddr)

        else:
            # treat as IPv4 address
            if ipaddr not in addrs:
                addrs.append(ipaddr)

    CACHE[name] = addrs

    if len(addrs6) > 0:
        CACHE6[name] = addrs6

    return addrs


def resolv6(name: str) -> List[str]:
    '''Returns list of IPv6 addresses for name
    Raises KeyError on error
    '''

    if name in CACHE6:
        return CACHE6[name]

    try:
        addr_arr = socket.getaddrinfo(name, 0, socket.AF_INET6)
    except socket.gaierror as err:
        raise KeyError(f"error resolving {name}") from err

    addrs = []
    for addr in addr_arr:
        ipaddr = addr[4][0]
        if ipaddr not in addrs:
            addrs.append(ipaddr)

    CACHE6[name] = addrs
    return addrs


def resolv4_and_6(name: str) -> List[str]:
    '''Returns list of both IPv4 and IPv6 addresses for name
    Raises KeyError on error
    '''

    addrs = []
    from_cache = False

    if name in CACHE:
        addrs.extend(CACHE[name])
        from_cache = True

    if name in CACHE6:
        addrs.extend(CACHE6[name])
        from_cache = True

    if from_cache:
        return addrs

    # let resolv() get both IPv4 and IPv6 address into the cache
    addrs = resolv(name)

    # again, look in cache for IPv6
    if name in CACHE6:
        addrs.extend(CACHE6[name])

    return addrs


# EOB
