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

from paramiko.server import SubsystemHandler
from parrot_log import Logger

class NETCONFsubsys (SubsystemHandler):
    cb_target = None

    @staticmethod
    def register_callback_object(cb_target):
        NETCONFsubsys.cb_target = cb_target
        Logger.debug(9, f'NETCONFsubsys: registered cb={cb_target}')

    def __init__(self, channel, name, server, *largs, **kwargs):
        Logger.debug(9, f'NETCONFsubsys: init channel={channel} name={name} server={server}')
        SubsystemHandler.__init__(self, channel, name, server)
        transport = channel.get_transport()
        self.ultra_debug = transport.get_hexdump()
        self.next_handle = 1
        Logger.debug(9, f'NETCONFsubsys: init done')

    def start_subsystem(self, name, transport, channel):
        Logger.debug(9, f'NETCONFsubsys: start_subsystem name={name} transport={transport} channel={channel}')
        self.sock = channel
        Logger.debug(9, 'Started NETCONF server on channel {!r}'.format(channel))
        try:
            self.handle_session()
        except Exception as e:
            Logger.error(f'NETCONFsubsys: callback exception {e}')
        Logger.info('Stopped NETCONF server on channel {!r}'.format(channel))

    def finish_subsystem(self):
        Logger.debug(9, f'NETCONFsubsys: finish_subsystem')
        self.server.session_ended()
        super(NETCONFsubsys, self).finish_subsystem()
        Logger.debug(9, 'NETCONF subsys finished')

    def handle_session(self):
        NETCONFsubsys.cb_target.handle_session()
