<div>
<ol>
 <li><a href="#whatis">What is firewater?</a></li>
 <li><a href="#install">Installing firewater</a></li>
 <li><a href="#using">Using firewater</a></li>
 <li><a href="#syntax">Input file syntax</a></li>
 <ol>
  <li><a href="#first">First an example</a></li>
  <li><a href="#iface">Interfaces</a></li>
  <li><a href="#network">Networks, ranges, hosts</a></li>
  <li><a href="#group">Logical groups</a></li>
  <li><a href="#service">Services</a></li>
  <li><a href="#policy">Default policy</a></li>
  <li><a href="#rule">Allow or deny</a></li>
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

<!-- the end -->
