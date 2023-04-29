#!/usr/bin/env python3
#
#   firewater.py    WJ111
#
#   firewater by Walter de Jong <walter@heiho.net> (c) 2012
#
#   firewater COMES WITH NO WARRANTY. firewater IS FREE SOFTWARE.
#   firewater is distributed under terms described in the GNU General Public
#   License.

'''build and install firewater'''

import os
import shutil

from distutils.core import setup

import firewater.globals

if not os.path.exists('build/etc/init.d'):
    os.makedirs('build/etc/init.d')
shutil.copy2('contrib/firewater.init', 'build/etc/init.d/firewater')

if not os.path.exists('build/etc/default'):
    os.makedirs('build/etc/default')
shutil.copyfile('contrib/firewater.default', 'build/etc/default/firewater')

if not os.path.exists('build/lib/systemd/system'):
    os.makedirs('build/lib/systemd/system')
shutil.copy2('contrib/firewater.service', 'build/lib/systemd/system/firewater.service')

setup(name='firewater',
      version=firewater.globals.VERSION,
      description='firewater host-based firewall',
      long_description='firewater host-based firewall',
      author='Walter de Jong',
      author_email='walter@heiho.net',
      url='http://www.heiho.net/software/',
      license='GPLv3',
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: Console',
                   'Intended Audience :: System Administrators',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Natural Language :: English',
                   'Operating System :: Unix',
                   'Programming Language :: Python',
                   'Topic :: System :: Networking :: Firewalls'
                  ],
      package_dir={'firewater': 'firewater'},
      packages=['firewater',],
      scripts=['scripts/firewater', 'scripts/firewater_main.py'],
      data_files=[('/etc/firewater.d',
                   ['firewater.d/allow_loopback.rules',
                    'firewater.d/allow_ping.rules',
                    'firewater.d/allow_established.rules',
                    'firewater.d/drop_invalid.rules',
                    'firewater.d/anti_spoofing.rules',
                    'firewater.d/anti_smurf.rules',
                    'firewater.d/reject_all.rules',
                    'firewater.d/logging.rules',
                    'firewater.d/log.rules'
                   ]),
                  ('/etc/init.d', ['build/etc/init.d/firewater',]),
                  ('/lib/systemd/system', ['build/lib/systemd/system/firewater.service',]),
                  ('/etc/default', ['build/etc/default/firewater',])
                 ]
     )

# EOB
