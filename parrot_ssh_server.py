# Based on demo_server.py from the Paramiko package
#
# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

import threading
import paramiko
from paramiko.py3compat import b, u, decodebytes
from binascii import hexlify
from parrot_log import Logger

# Workaround for https://github.com/paramiko/paramiko/issues/1455
from paramiko import transport
transport.Transport._preferred_kex = (
        'ecdh-sha2-nistp256',
        'ecdh-sha2-nistp384',
        'ecdh-sha2-nistp521',
        # 'diffie-hellman-group16-sha512',  # disable
        'diffie-hellman-group-exchange-sha256',
        #'diffie-hellman-group14-sha256',
        'diffie-hellman-group-exchange-sha1',
        'diffie-hellman-group14-sha1',
        'diffie-hellman-group1-sha1',
)

paramiko.util.log_to_file('ncparrot.log')
#host_key = paramiko.RSAKey(filename='ncparrot.rsa.key')
#print('Read key: ' + u(hexlify(host_key.get_fingerprint())))

class Server (paramiko.ServerInterface):
    def __init__(self):
        Logger.debug(9, f'SSH Server: init')
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        Logger.debug(9, f'SSH Server: check_channel_request kind={kind} chanid={chanid}')
        if kind == 'session':
            Logger.debug(9, f'SSH Server: check_channel_request accepted')
            return paramiko.OPEN_SUCCEEDED
        Logger.debug(9, f'SSH Server: check_channel_request rejected')
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        Logger.debug(9, f'SSH Server: check_auth_password')
        # No real authenticatio, all users welcome
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        Logger.debug(9, f'SSH Server: check_auth_publickey')
        # No real authenticatio, all users welcome
        return paramiko.AUTH_SUCCESSFUL
    
    def check_auth_gssapi_with_mic(self, username,
                                   gss_authenticated=paramiko.AUTH_FAILED,
                                   cc_file=None):
        Logger.debug(9, f'SSH Server: check_auth_gssapi_with_mic')
        # No real authenticatio, all users welcome
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_gssapi_keyex(self, username,
                                gss_authenticated=paramiko.AUTH_FAILED,
                                cc_file=None):
        Logger.debug(9, f'SSH Server: check_auth_gssapi_keyex')
        # No real authenticatio, all users welcome
        return paramiko.AUTH_SUCCESSFUL

    def enable_auth_gssapi(self):
        Logger.debug(9, f'SSH Server: enable_auth_gssapi')
        return True

    def get_allowed_auths(self, username):
        Logger.debug(9, f'SSH Server: get_allowed_auths')
        return 'gssapi-keyex,gssapi-with-mic,password,publickey'

    def check_channel_shell_request(self, channel):
        Logger.debug(9, f'SSH Server: check_channel_shell_request')
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        Logger.debug(9, f'SSH Server: check_channel_pty_request')
        return True
