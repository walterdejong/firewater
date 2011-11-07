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
<h2 id="whatis">What is firewater?</h2>
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
<h2 id="install">Installing firewater</h2>
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

<!-- the end -->
