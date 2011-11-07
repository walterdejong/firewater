<div>
<ol>
 <li><a href="#whatis">What is firewater?</a></li>
 <li><a href="#install">Installing firewater</a></li>
 <li><a href="#using">Using firewater</a></li>
 <li><a href="#syntax">Input file syntax</a></li>
 <ol>
  <li><a href="#example_config">Example configuration</a></li>
  <li><a href="#iface">Interfaces</a></li>
  <li><a href="#network">Networks, ranges, hosts</a></li>
  <li><a href="#group">Logical groups</a></li>
  <li><a href="#service">Services</a></li>
  <li><a href="#policy">Default policy</a></li>
  <li><a href="#rule">Rules: allow or deny</a></li>
  <li><a href="#ifdef">Conditional statements: Using ifdefs</a></li>
  <li><a href="#echo">Injecting native firewall commands</a></li>
  <li><a href="#include">Standard includes</a></li>
  <li><a href="#list">List of all keywords</a></li>
 </ol>
</ol>
</div>

<div>
<h2 id="whatis">1. What is firewater?</h2>
<p>
firewater is a(nother) hostbased firewall configuration tool.
It offers a simple way to compose firewall policies from the command prompt,
without the need for a GUI.
</p>
<p>
firewater lowers the steep learning curve that native firewalling commands
have. firewater features user-definable logical groups to keep your policies
(or rules) readable and easy to understand.
For maximum flexibility, typical firewater statements may be intermixed
with native commands to the underlying system-specific firewall.
</p>
<p>
firewater currently only works with Linux iptables, but is extensible
through its modular architecture so that it may support more firewalling
systems in the future.
</p>
</div>

<div>
<h2 id="install">2. Installing firewater</h2>
<p>
For installing the software, in short, do the following (as root):
<div class="example">
./setup.py install
</div>
</p>
<p>
If you want to use the provided init-script for Linux, also do
these steps:
<div class="example">
cp contrib/firewater.init /etc/init.d/firewater<br />
cp contrib/firewater.default /etc/default/firewater<br />
touch /etc/firewater.rules
</div>
Use <span class="cmd">chkconfig</span> or <span class="cmd">update-rc.d</span>
or whatever to activate the init script.
Edit <span class="path">/etc/default/firewater</span> as you wish.
</p>
<p>
Setup your rules using <span class="cmd">vi</span> (or editor of choice)
in <span class="path">/etc/firewater.rules<span>. Then call:
<div class="example">
/etc/init.d/firewater test<br />
/etc/init.d/firewater commit
</div>
</p>
</div>

<div>
<h2 id="using">3. Using firewater</h2>
<p>
firewater is an application that acts as a translator. It translates firewater
input rules into statements that the native firewall can understand.
For example, for Linux this means that firewater rules are translated into
<span class="cmd">iptables</span> statements. [In theory, firewater can
translate for other targets as well, but this is currently not implemented.]
</p>
<p>
Because firewater is only a translator, it does not directly act on your
active firewall. This allows you to test and tweak your configuration
before committing and loading the new rules into the firewall. firewater
comes with an <span class="system">init.d</span> script that makes it
easy to reload Linux's <span class="cmd">iptables</span> firewall with
your firewater configuration.
</p>
<p>
An example of running firewater:
<div class="example">
$ /usr/local/bin/firewater --verbose -DTEST /etc/firewater.rules | less
</div>
In this example, the configuration in <span class="path">/etc/firewater.rules</span>
is translated. The output is piped through a pager
(named <span class="cmd">less</span>). In verbose output mode, firewater
will display the source rules in comments in between the translated output
lines. Lastly, a user-defined symbol <span class="system">TEST</span> is
defined; the input rules may check for the existence of this define and
act upon this.
</p>
<p>
A second example of how to use firewater:
<div class="example">
# service firewater test<br />
# service firewater commit
</div>
In this example, the <span class="system">root</span> user invokes the
firewater wrapper script under <span class="path">/etc/init.d/</span>
to test and commit (load) the new firewall.
</p>
</div>

<div>
<h2 id="syntax">4. Input file syntax</h2>
<p>
As input, firewater accepts text files. A text file contains a firewater rule
set. Firewater rule sets are line based, and every line starts with a keyword.
Comments are marked with a &lsquo;<span class="system">#</span>&rsquo; hash token.
Comments may be started at the beginning of a line, but can also be added to
the end of a line.
</p>
<p>
The following subsections explain the keywords of the syntax of the input.
</p>
</div>

<div>
<h2 id="example_config">4.1 Example configuration</h2>
<p>
For those who learn by example, here is an example configuration:
<div class="example">
# this line is comment<br />
<br />
iface public   eth0<br />
iface internal eth1<br />
iface all-interfaces eth0,eth1,eth1.vlan10<br />
<br />
host myhost  myhostname.fqdn.org<br />
host myhost2 127.0.1.18<br />
<br />
host google  74.125.79.99, 74.125.79.100, 74.125.79.101<br />
<br />
network internal-network  192.168.1.0/16<br />
<br />
group search-engines  google, www.yahoo.com, \<br />
&nbsp; &nbsp; &nbsp;  www.altavista.com, www.bing.com, \<br />
&nbsp; &nbsp; &nbsp;  sogou.com, soso.com, 127.123.12.34<br />
<br />
service myservice tcp 1234<br />
<br />
chain incoming default policy drop<br />
chain outgoing default policy accept<br />
<br />
include /etc/firewater.d/anti_spoofing.rules<br />
<br />
<br />
# it's just an example<br />
allow tcp from any to myhost port ssh on public interface<br />
<br />
# it's just an example<br />
deny tcp from search-engines to internal-network<br />
<br />
include /etc/firewater.d/reject_all.rules<br />
<br />
<br />
ifdef TEST<br />
  echo This is a test !!!<br />
endif<br />
<br />
# inject iptables rules<br />
verbatim<br />
-I INPUT -i lo -j ACCEPT<br />
-I FORWARD -o lo -j ACCEPT<br />
-I FORWARD -i lo -j ACCEPT<br />
end<br />
</div>
</p>
</div>

<div>
<h2 id="iface">4.2 Interfaces</h2>
<p>
Firewalls, and thus firewater too, work with interfaces. An interface is the
software representation of the hardware network port on your network card.
[If you use virtual LANs (VLANs) or software drivers like PPP you may have
additional interfaces that only exist in software.]
You can see your interfaces with the <span class="smallcaps">UNIX</span>
command <span class="cmd">ifconfig -a</span>.
In Linux, you may also use the command <span class="cmd">ip addr show</span>.
</p>
<p>
In firewater you can give these interfaces logical names using the
<span class="system">iface</span> keyword. Moreover, you can group multiple
interfaces together under a single <span class="system">iface</span> definition.
<div class="example">
iface public eth0<br />
iface mgmt eth1<br />
<br />
iface internet eth0<br />
iface internal eth1,eth2,eth2.vlan10,ppp0<br />
<br />
iface if-ext eth0<br />
iface if-wlan eth1<br />
iface if-test eth2<br />
</div>
</p>
<p>
For naming, you may choose whatever you see fit. It is good however to have
an interface named <span class="system">public</span> because firewater comes
with a set of anti-spoofing rules which work on an interface named &lsquo;public&rdquo;.
</p>
<p>
It is not mandatory to use <span class="system">iface</span> definitions, but
they make writing rules easier.
</p>
</div>

<div>
<h2 id="network">4.3 Networks, ranges, hosts</h2>
<p>
TCP/IP networking revolves around IP addresses. In firewater you can define
logical names for IP adresses or for ranges of IP addresses.
<div class="example">
host myhost 123.124.12.34<br />
host myhost2 myhostname.fqdn.org<br />
<br />
network localnet 10.0.0.0/8<br />
<br />
range classb 192.168.0.0/16
</div>
As you can see, both names and addresses can be used for creating host aliases.
firewater can use DNS to resolve names so you don't have to explicitly list
all hosts by address. However, it is often nice to use a short alias for a
host rather than its fully qualified domain name.
</p>
<p>
Note that the <span class="system">network</span> keyword is merely an alias for
the <span class="system">range</span> keyword; they have the exact same
meaning.
</p>
<p>
Like with interfaces, it is not mandatory to use any of these, but they make
maintaining your ruleset easier.
</p>
<p>
IPv6 addresses are supported, just not very well tested.
</p>
</div>

<div>
<h2 id="group">4.4 Logical groups</h2>
<p>
Now that we have defined multiple hosts and network ranges, you can group them
together like this:
<div class="example">
group myhosts myhost, myhost2<br />
<br />
group mystuff myhosts, mynetwork<br />
<br />
group somegroup myhost.fqdn.org, 128.12.23.45, 128.19.0.0/24<br />
<br />
group evil-hosts  a.spammer.net, a.cracker.net<br />
group good-hosts  grandma, grandpa, localhost
</div>
</p>
As you can see, groups can also be part of other groups.
If you use groups in a clever way, it will be easy to maintain a ruleset.
<p>
</p>
</div>

<div>
<h2 id="service">4.5 Services</h2>
<p>
Network services use well-known port numbers. For example, the SSH service
uses TCP port 22. The SSH daemon listens on TCP port 22 for connections,
and the SSH client connects to TCP port 22 to establish a connection.
The port numbers for well-known services are typically listed in
<span class="system">/etc/services</span>.
However, it is perfectly possible to run a service on a port number that is
not listed in <span class="system">/etc/services</span>. In firewater you can
define your own local services so that you can write rules using the logical
service names rather than having to use port numbers.
<div class="example">
service myhttp tcp 8080<br />
service ssh-test tcp 222<br />
service udp-test udp 10000<br />
service globus-range tcp 20000-25000<br />
</div>
As you can see, in firewater it is possible to define a port range for
a given service.
</p>
<p>
There is no need to declare any services in firewater that already exist in
<span class="system">/etc/services</span>.
</p>
</div>

<div>
<h2 id="policy">4.6 Default policy</h2>
<p>
Firewalls deal with packets of network traffic coming into your computer via
the network interface and going out of your computer through the network
interface again. You set a default policy of what to do with a packet,
do you want to accept it or do you want to drop it? Dropping means denying,
accepting means allowing it to go through. The default policy must be set
(only once), the ruleset will act like an amendment to the default policy.
So it is okay to block everyone (default policy drop) and later add a
rule saying that it's okay to let your mother in.
</p>
<p>
The <span class="system">incoming</span> and <span class="system">outgoing</span>
components are called <em>chains</em>. Linux has a forwarding chain that is used
for routing. Any rules that you define operate on one (and exactly one) of these
chains. It is important to tell firewater what chain your rules should work on.
You can do so using the same <span class="system">chain</span> keyword as for
setting the default policy.
</p>
<p>
Example for a setup that by default blocks all (presumably evil) machines
from trying to connect to your computer, but allows you to freely use the
internet:
<div class="example">
chain incoming policy drop<br />
chain outgoing policy accept<br />
chain forwarding policy accept<br />
<br />
# very important: set the current chain to incoming<br />
chain incoming<br />
</div>
Remember to set the current chain (!) before adding new rules.
</p>
</div>

<div>
<h2 id="rule">4.7 Rules: allow or deny</h2>
<p>
Firewalls are all about allowing traffic to go through or not. In a rule you
specify where a packet comes from, what its destination may be, what service
port it may use, on what interface it occurs, and whether it is allowed or
denied.
<div class="example">
allow tcp from any to mywebserver port http on public interface<br />
allow tcp from good-hosts to mynetwork port ssh on public interface<br />
allow tcp from mgmt-lan to mgmt-lan on mgmt interface<br />
<br />
# 'any' is a wildcard, meaning '0.0.0.0/0'<br />
deny from bad-hosts to any<br />
<br />
# with source port:<br />
allow udp from server1 port 8000 to myhost<br />
<br />
# with port range:<br />
allow tcp from grid-hosts to grid-server port globus-range on iface if-grid<br />
<br />
# with fqdn and numbers:<br />
allow tcp from host1.servers.net to 123.123.12.34 port 80
</div>
Both the syntax &ldquo;<span class="system">on iface ...</span>&rdquo; and
&ldquo;<span class="system">on ... interface</span>&rdquo; may be used.
It is allowed to omit the interface, in which case the rule will apply to all
interfaces.
</p>
</div>

<div>
<h2 id="ifdef">4.8 Conditional statements: Using ifdefs</h2>
<p>
firewater has a mechanism for letting you to choose whether to include a block
of rules or not. This is convenient for a number of reasons:
<ul>
 <li>For testing you want to enable some rules;</li>
 <li>You temporarily want to disable some rules;</li>
 <li>In a group of machines, all but one have the same firewall config;</li>
 <li>In a group of machines, some have different interfaces;</li>
 <li>The services you offer, and thus your firewalling stanza, switches regularly</li>
</ul>
firewater uses user-definable symbols and <span class="system">ifdef</span>s
to facilitate this. The symbols are passed on the command-line using the
<span class="system">-D</span> parameter.
<div class="example">
$ firewater -DTEST -DWEBSERVER firewater.rules<br />
<br />
<br />
ifdef TEST<br />
&nbsp; echo this is a test!<br />
endif<br />
<br />
ifdef WEBSERVER<br />
&nbsp; allow tcp from any to any port http<br />
&nbsp; allow tcp from any to any port https<br />
endif<br />
<br />
ifndef EXTRA_NIC<br />
&nbsp; iface public eth0<br />
else<br />
&nbsp; iface public eth1<br />
endif
</div>
<span class="system">ifdef</span>s may be nested. Note that unlike in the
C programming language, <span class="system">ifdef</span> statements do not
start with a <span class="system">#</span>-token because in firewater those
are treated as comments.
</p>
</div>

<div>
<h2 id="echo">4.9 Injecting native firewall commands</h2>
<p>
firewater translates <em>firewater</em> rules into statements for the target
firewalling tool. The default target firewalling tool is Linux
<span class="cmd">iptables</span>. firewater's command set is limited and
<span class="cmd">iptables</span> has a very extensive command set.
firewater offers two ways that allow you to inject native firewall commands
into firewater's output: the <span class="system">echo</span> keyword and
the <span class="system">verbatim</span> keyword.
<div class="example">
echo -A INPUT -m limit --limit 30/min -j LOG --log-prefix "iptables dropping: "<br />
<br />
verbatim<br />
-I INPUT -i lo -j ACCEPT<br />
-I FORWARD -o lo -j ACCEPT<br />
-I FORWARD -i lo -j ACCEPT<br />
end
</div>
This example shows how <span class="system">echo</span> and
<span class="system">verbatim</span> can be used to inject explicit
<span class="cmd">iptables</span> commands into firewater's output.
</p>
</div>


<!-- the end -->
