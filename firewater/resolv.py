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

CACHE = {}
CACHE6 = {}


def resolv(name):
    '''Returns array of IPv4 addresses for name
    or None on error
    '''

    if CACHE.has_key(name):
        return CACHE[name]

    try:
        addr_arr = socket.getaddrinfo(name, 0, socket.AF_UNSPEC)
    except socket.gaierror:
#       stderr('error resolving %s' % name)
        return None

    addrs = []
    addrs6 = []
    for addr in addr_arr:
        ipaddr = addr[4][0]

        if ipaddr.find(':') > -1:
            # treat as IPv6 address
            if not ipaddr in addrs6:
                addrs6.append(ipaddr)

        else:
            # treat as IPv4 address
            if not ipaddr in addrs:
                addrs.append(ipaddr)

    CACHE[name] = addrs

    if len(addrs6) > 0:
        CACHE6[name] = addrs6

    return addrs


def resolv6(name):
    '''returns array of IPv6 addresses for name
    or None on error
    '''

    if CACHE6.has_key(name):
        return CACHE6[name]

    try:
        addr_arr = socket.getaddrinfo(name, 0, socket.AF_INET6)
    except socket.gaierror:
#       stderr('error resolving %s' % name)
        return None

    addrs = []
    for addr in addr_arr:
        ipaddr = addr[4][0]
        if not ipaddr in addrs:
            addrs.append(ipaddr)

    CACHE6[name] = addrs
    return addrs


def resolv4_and_6(name):
    '''returns array of both IPv4 and IPv6 addresses for name
    or None on error
    '''

    addrs = []
    from_cache = False

    if CACHE.has_key(name):
        addrs.extend(CACHE[name])
        from_cache = True

    if CACHE6.has_key(name):
        addrs.extend(CACHE6[name])
        from_cache = True

    if from_cache:
        return addrs

    # let resolv() get both IPv4 and IPv6 address into the cache
    addrs = resolv(name)
    if addrs is None:   # error
        return None

    # again, look in cache for IPv6
    if CACHE6.has_key(name):
        addrs.extend(CACHE6[name])

    return addrs

# EOB
