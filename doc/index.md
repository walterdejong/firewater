* [What is firewater?](#what-is-firewater)
* [Installing firewater](#installing-firewater)
 - [Creating a package](#creating-a-package)
 - [Enabling firewater at boot time](#enabling-firewater-at-boot-time)
* [Using firewater](#using-firewater)
* [Input file syntax](#input-file-syntax)
 - [Example configuration](#example-configuration)
 - [Interfaces](#interfaces)
 - [Networks, ranges, hosts](#networks-ranges-hosts)
 - [Logical groups](#logical-groups)
 - [Services](#services)
 - [Default policy](#default-policy)
 - [Rules: allow or deny](#rules-allow-or-deny)
 - [Conditional statements: Using ifdefs](#conditional-statements-using-ifdefs)
 - [Injecting native firewall commands](#injecting-native-firewall-commands)
 - [Standard includes](#standard-includes)
 - [List of all keywords](#list-of-all-keywords)


1. What is firewater? <a name="what-is-firewater"></a>
---------------------
firewater is a(nother) host-based firewall configuration tool.
It offers a simple way to compose firewall policies from the command prompt,
without the need for a GUI.

firewater lowers the steep learning curve that native firewalling commands
have. firewater features user-definable logical groups to keep your policies
(or rules) readable and easy to understand.
For maximum flexibility, typical firewater statements may be intermixed
with native commands to the underlying system-specific firewall.

firewater currently only works with Linux `iptables`,
but is extensible through its modular architecture so that it may support
more firewalling systems in the future.


2. Installing firewater <a name="installing-firewater"></a>
-----------------------
For installing the software, in short, do the following (as root):

    # ./setup.py install

The firewall does _nothing_ until you configure it, start it, and
enable it at boot time.

Review and edit `/etc/default/firewater` for some basic settings.


2.1 Creating a package <a name="creating-a-package"></a>
----------------------
On Redhat, CentOS, SUSE and other RPM based distributions you may
create a package by using distutils. You can create the package by
running the following command:

    $ python ./setup.py bdist_rpm

On Debian based systems, run:

    $ fakeroot debian/rules binary

You can also create a `.tar.gz` based install:

    $ python ./setup.py bdist


2.2 Enabling firewater at boot time <a name="enabling-firewater-at-boot-time"></a>
-----------------------------------
Installing firewater _does not_ start the firewall, nor enable it
at boot time. The reason for this is that you must first edit
`/etc/firewater.rules` and make a decent ruleset.

A committed ruleset persists across reboots, but _only if_ firewater
has been enabled in the boot process.

On systems that use SysV init:

    # chkconfig firewater on

    # service firewater status
    # service firewater start

or

    # update-rc.d firewater defaults

    # service firewater status
    # service firewater start

On systems that use systemd:

    # systemctl enable firewater.service

    # systemctl status -l firewater.service
    # systemctl start firewater.service


3. Using firewater <a name="using-firewater"></a>
------------------
firewater is an application that acts as a translator. It translates firewater
input rules into statements that the native firewall can understand.
For Linux this means that firewater rules are translated to `iptables`
statements. (In theory, firewater can translate for other targets as well,
but this is currently not implemented).

Because firewater is only a translator, it does not directly act on your
active firewall. This allows you to test and tweak your configuration
before committing and loading the new rules into the firewall.

Setup your rules using `vi` (or editor of choice) in `/etc/firewater.rules`.
Beware that making a mistake might lock you out of the system, in the
beginning you may want to start with a simple ruleset that only logs things.

Next, test the ruleset (verify that there are no syntax errors) and
it must be committed to take effect. The Linux firewall is reloaded upon
commit.

    # vim /etc/firewater.rules

    # firewater test |less

    # firewater commit

Remember: Whenever the ruleset is changed, it must be tested and committed,
otherwise the rules are not active.


4. Input file syntax <a name="input-file-syntax"></a>
--------------------
As input, firewater accepts text files. A text file contains a firewater rule
set. Firewater rule sets are line based, and every line starts with a keyword.
Comments are marked with a '#' hash token.
Comments may be started at the beginning of a line, but can also be added to
the end of a line.

The following subsections explain the keywords of the syntax of the input.


4.1 Example configuration <a name="example-configuration"></a>
-------------------------
For those who learn by example, here is an example configuration:

    # this line is comment
    
    iface public   eth0
    iface internal eth1
    iface all-interfaces eth0,eth1,eth1.vlan10
    
    host myhost  myhostname.fqdn.org
    host myhost2 127.0.1.18
    
    host google  74.125.79.99, 74.125.79.100, 74.125.79.101
    
    network internal-network  192.168.1.0/16
    
    group search-engines  google, www.yahoo.com, \
           www.altavista.com, www.bing.com, \
           sogou.com, soso.com, 127.123.12.34
    
    service myservice tcp 1234
    
    chain incoming default policy drop
    chain outgoing default policy accept
    
    include /etc/firewater.d/anti_spoofing.rules
    
    
    # it's just an example
    allow tcp from any to myhost port ssh on public interface
    
    # it's just an example
    deny tcp from search-engines to internal-network
    
    include /etc/firewater.d/reject_all.rules
    
    
    ifdef TEST
      echo This is a test !!!
    endif
    
    # inject iptables rules
    verbatim
    -I INPUT -i lo -j ACCEPT
    -I FORWARD -o lo -j ACCEPT
    -I FORWARD -i lo -j ACCEPT
    end


4.2 Interfaces <a name="interfaces"></a>
--------------
Firewalls, and thus firewater too, work with interfaces. An interface is the
software representation of the hardware network port on your network card.
[If you use virtual LANs (VLANs) or software drivers like PPP you may have
additional interfaces that only exist in software.]
You can see your interfaces with the <span class="smallcaps">UNIX</span>
command `ifconfig -a`.
In Linux, you may also use the command `ip addr show`.

In firewater you can give these interfaces logical names using the
`iface` keyword. Moreover, you can group multiple interfaces together under
a single `iface` definition.

    iface public eth0
    iface mgmt eth1
    
    iface internet eth0
    iface internal eth1,eth2,eth2.vlan10,ppp0
    
    iface if-ext eth0
    iface if-wlan eth1
    iface if-test eth2

For naming, you may choose whatever you see fit. It is good however to have
an interface named `public` because firewater comes with a set of
anti-spoofing rules which work on an interface named "public".

It is not mandatory to use `iface` definitions, but they make life easier.


4.3 Networks, ranges, hosts <a name="networks-ranges-hosts"></a>
---------------------------
TCP/IP networking revolves around IP addresses. In firewater you can define
logical names for IP adresses or for ranges of IP addresses.

    host myhost 123.124.12.34
    host myhost2 myhostname.fqdn.org
    
    network localnet 10.0.0.0/8
    
    range classb 192.168.0.0/16

As you can see, both names and addresses can be used for creating
host aliases. firewater can use DNS to resolve names so you don't have
to explicitly list all hosts by address. However, it is often nice to use
a short alias for a host rather than its fully qualified domain name.

Note that the `network` keyword is merely an alias for the `range` keyword;
they have the exact same meaning.

Like with interfaces, it is not mandatory to use any of these, but they make
maintaining your ruleset easier.

Although firewater understands IPv6 addresses, IPv6 is not really supported.


4.4 Logical groups <a name="logical-groups"></a>
------------------
Now that we have defined multiple hosts and network ranges, you can group them
together like this:

    group myhosts myhost, myhost2
    
    group mystuff myhosts, mynetwork
    
    group somegroup myhost.fqdn.org, 128.12.23.45, 128.19.0.0/24
    
    group evil-hosts  a.spammer.net, a.cracker.net
    group good-hosts  grandma, grandpa, localhost

As you can see, groups can also be part of other groups.
If you use groups in a clever way, it will be easy to maintain a ruleset.


4.5 Services <a name="services"></a>
------------
Network services use well-known port numbers. For example, the SSH service
uses TCP port 22. The SSH daemon listens on TCP port 22 for connections,
and the SSH client connects to TCP port 22 to establish a connection.
The port numbers for well-known services are typically listed in
`/etc/services`.
However, it is perfectly possible to run a service on a port number that is
not listed in `/etc/services`. In firewater you can define your own
local services so that you can write rules using the logical service names
rather than having to use port numbers.

    service myhttp tcp 8080
    service ssh-test tcp 222
    service udp-test udp 10000
    service globus-range tcp 20000-25000

As you can see, it is possible to define a port range for a service.

There is no need to declare any services in firewater that already exist in
`/etc/services`.


4.6 Default policy <a name="default-policy"></a>
------------------
Firewalls deal with packets of network traffic coming into your computer via
the network interface and going out of your computer through the network
interface again. You set a default policy of what to do with a packet,
do you want to accept it or do you want to drop it? Dropping means denying,
accepting means allowing it to go through. The default policy must be set
(only once), the ruleset will act like an amendment to the default policy.
So it is okay to block everyone (default policy drop) and later add a
rule saying that it's okay to let your mother in.

The `incoming` and `outgoing` components are called _chains_.
Linux has a forwarding chain that is used for routing. Any rules that
you define operate on one (and exactly one) of these chains. It is important
to tell firewater what chain your rules should work on. You can do so using
the same `chain` keyword as for setting the default policy.

Example for a setup that by default blocks all (presumably evil) machines
from trying to connect to your computer, but allows you to freely use the
internet:

    chain incoming policy drop
    chain outgoing policy accept
    chain forwarding policy accept
    
    # very important: set the current chain to incoming
    chain incoming

Remember to set the current chain (!) before adding new rules.


4.7 Rules: allow or deny <a name="rules-allow-or-deny"></a>
------------------------
Firewalls are all about allowing traffic to go through or not. In a rule you
specify where a packet comes from, what its destination may be, what service
port it may use, on what interface it occurs, and whether it is allowed or
denied.

    allow tcp from any to mywebserver port http on public interface
    allow tcp from good-hosts to mynetwork port ssh on public interface
    allow tcp from mgmt-lan to mgmt-lan on mgmt interface
    
    # 'any' is a wildcard, meaning '0.0.0.0/0'
    deny from bad-hosts to any
    
    # with source port:
    allow udp from server1 port 8000 to myhost
    
    # with port range:
    allow tcp from grid-hosts to grid-server port globus-range on iface if-grid
    
    # with fqdn and numbers:
    allow tcp from host1.servers.net to 123.123.12.34 port 80

Both the syntax `on iface ...` and `on ... interface` may be used.
It is allowed to omit the interface, in which case the rule will apply
to all interfaces.


4.8 Conditional statements: Using ifdefs <a name="conditional-statements-using-ifdefs"></a>
----------------------------------------
firewater has a mechanism for letting you to choose whether to include a block
of rules or not. This is convenient for a number of reasons:

* For testing you want to enable some rules;
* You temporarily want to disable some rules;
* In a group of machines, all but one have the same firewall config;
* In a group of machines, some have different interfaces;
* The services you offer, and thus your firewall config, switches regularly

firewater uses user-definable symbols and `ifdef`s to facilitate this.
The symbols may be defined in `/etc/default/firewater` as `EXTRA_OPTIONS`;
they are passed on the command-line using the `-D` parameter.

    $ firewater_main.py -DTEST -DWEBSERVER /etc/firewater.rules

    ifdef TEST
      echo this is a test!
    endif
    
    ifdef WEBSERVER
      allow tcp from any to any port http
      allow tcp from any to any port https
    endif
    
    ifndef EXTRA_NIC
      iface public eth0
    else
      iface public eth1
    endif

`ifdef`s may be nested. Note that unlike in the C programming language,
`ifdef` statements do not start with a `#`-token because in firewater those
are treated as comments.


4.9 Injecting native firewall commands <a name="injecting-native-firewall-commands"></a>
--------------------------------------
firewater translates <em>firewater</em> rules into statements for the target
firewalling tool. The default target firewalling tool is Linux `iptables`.
firewater's command set is limited and `iptables` has a very extensive
command set. firewater offers two ways that allow you to inject native
firewall commands into firewater's output: the `echo` keyword and
the `verbatim` keyword.

    echo -A INPUT -m limit --limit 30/min -j LOG --log-prefix "iptables dropping: "
    
    verbatim
    -I INPUT -i lo -j ACCEPT
    -I OUTPUT -o lo -s 127.0.0.0/8 -j ACCEPT
    end

This example shows how `echo` and `verbatim` can be used to inject explicit
`iptables` commands into firewater's output.


4.10 Standard includes <a name="standard-includes"></a>
----------------------
Using the `include` keyword, it is possible to include other ruleset files:

    include /etc/firewater.d/allow_loopback.rules
    include /etc/firewater.d/anti_spoofing.rules
    include /etc/firewater.d/allow_established.rules
    
    # ... put some rules here ...
    
    include /etc/firewater.d/logging.rules

A number of standard includes come with the package, they are situated
under `/etc/firewater.d/`. Provided are standard rules like for allowing
traffic on the loopback interface, rules that block spoofing attempts,
rules for logging to syslog, and more.


4.11 List of all keywords <a name="list-of-all-keywords"></a>
-------------------------
`allow [tcp|udp|ip|icmp|gre] [from SRC [port SERVICE]] [to DEST [port SERVICE]]
[on [interface|iface] IFACE [interface]]`
Rule that allows traffic to go through

`chain incoming|outgoing|forwarding [policy accept|deny|allow|drop]`
Select current chain, optionally setting default policy

`define SYMBOL`
Define a new user-definable symbol, to be used with an `ifdef` statement

`deny [tcp|udp|ip|icmp|gre] [from SRC [port SERVICE]] [to DEST [port SERVICE]]
[on [interface|iface] IFACE [interface]]`
Rule that blocks traffic from going through

`echo LINE`
Prints a line of text to standard output

`else`
Conditional statement that evaluates to true if the preceding
`ifdef` or `ifndef` was not true

`end`
Signifies the end of a `verbatim` block

`endif`
Signifies the end of a conditional block

`exit [CODE]`
Terminate the translation, possibly with a given exit code

`group ALIAS MEMBER [, ...]`
Define a new group of hosts and/or network ranges

`host ALIAS IPADDR|FQDN`
Define a new alias for a given host

`iface ALIAS SYSTEM_INTERFACE_NAME [, ...]`
Define a new alias for an interface or collection of interfaces

`ifdef SYMBOL`
Include the following conditional block if the symbol is defined

`ifndef SYMBOL`
Include the following conditional block if the symbol is not defined

`include FILENAME`
Include a file containing a firewater ruleset

`interface ALIAS SYSTEM_INTERFACE_NAME [, ...]`
Alias for `iface`

`network ALIAS ADDRESS_RANGE`
Alias for `range`

`range ALIAS ADDRESS_RANGE`
Define a new alias for an IP address range

`serv ALIAS tcp|udp PORT`
Define a new alias for a network service

`service ALIAS tcp|udp PORT`
Alias for `serv`

`verbatim`
Copy block of text to standard output until the `end` keyword is reached

<!-- the end -->
