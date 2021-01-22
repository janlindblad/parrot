# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

import sys, time, socket

from parrot_log import Logger
from parrot_ssh_subsystem import NETCONFsubsys
from parrot_ssh_server import Server
from paramiko import Transport, SSHException, RSAKey, util

## Workaround for https://github.com/paramiko/paramiko/issues/1455
#from paramiko import transport
#transport.Transport._preferred_kex = (
#        'ecdh-sha2-nistp256',
#        'ecdh-sha2-nistp384',
#        'ecdh-sha2-nistp521',
#        # 'diffie-hellman-group16-sha512',  # disable
#        'diffie-hellman-group-exchange-sha256',
#        #'diffie-hellman-group14-sha256',
#        'diffie-hellman-group-exchange-sha1',
#        'diffie-hellman-group14-sha1',
#        'diffie-hellman-group1-sha1',
#)

from parrot_message import Message, XML_Message
from parrot_server import YANG_Server

class NETCONF_Server(YANG_Server):
  netconf_version = 10
  instance = None

  @staticmethod
  def set_instance(instance):
    NETCONF_Server.instance = instance
    NETCONFsubsys.register_callback_object(instance)

  def __init__(self):#, name, subsys=NETCONFsubsys):
    self.name = "NETCONF_Server" # FIXME: used for anything?
    self.sock = None
    self.channel = None
    self.subsys = NETCONFsubsys
    self.netconf_ver = 10
    self.msg_id = 0
    self.indata = b""
    self.delimiter10 = "]]>]]>".encode('utf-8')
    self.delimiter11 = "\n##\n".encode('utf-8')
    self.logging_peek_length = 80
    self.host = ''
    self.port = 8299
    self.host_key_filename = 'hostkey2' #FIXME 'ncparrot.rsa.key'

  def set_host_port(self, host, port):
    self.host = host
    self.port = port

  def listen(self):
    NETCONF_Server.set_instance(self)
    try:
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      #sock.bind(('', self.port))
      sock.bind((self.host, self.port))
    except Exception as e:
      Logger.fatal('Bind failed: ' + str(e))

    try:
      sock.listen(100)
    except Exception as e:
      Logger.fatal('Listen failed: ' + str(e))
    Logger.info(f'Listening for connections on port {self.port}...')

    #host_key = RSAKey(filename=self.host_key_filename)
    host_key = RSAKey.generate(2048)

    while True:
      try:
        client, addr = sock.accept()
      except Exception as e:
        Logger.fatal('Accept failed: ' + str(e))
      self.sock = client
      Logger.info(f'Client {addr} connected')
      self.handle_connection(host_key)
      Logger.info(f'Client {addr} disconnected')

  def handle_connection(self, host_key):
    try:
      DoGSSAPIKeyExchange = False
      t = Transport(self.sock, gss_kex=DoGSSAPIKeyExchange)
      t.set_subsystem_handler('netconf', self.subsys)
      t.set_gss_host(socket.getfqdn(""))
      try:
        t.load_server_moduli()
      except:
        Logger.warning('Failed to load moduli -- gex will be unsupported.')
      t.add_server_key(host_key)
      server = Server()
      t.start_server(server=server)

      # wait for auth
      self.channel = t.accept(20)
      if self.channel is None:
        Logger.error('No SSH channel')
        return

      Logger.info('Waiting for message')
      server.event.wait(10000)
      Logger.info('Closing')
      self.channel.close()
      Logger.info('Client connection closed')
    except ConnectionResetError as e:
      Logger.info('Connection reset by peer')
    except SSHException:
      Logger.error('SSH negotiation failed, client connection dropped')
    except Exception as e:
      Logger.error('Caught exception: ' + str(e.__class__) + ': ' + str(e))
      traceback.print_exc()
      try:
        t.close()
      except:
        pass

  def receive_message(self, xml_text):
    return self.reply(XML_Message(xml_text))

  def reply(self, incoming_message):
    raise Exception("Abstract NETCONF_Server can't reply to any message")

  def handle_session(self):
    Logger.debug(6, 'Session loop running')
    self.incoming_message('<?xml version="1.0" encoding="UTF-8"?><hello xmlns="parrot"/>')
    while True:
      try:
        Logger.info('NETCONF server ready, waiting for next message')
        msg = self.read_msg()
      except EOFError:
        Logger.debug(5,'EOF -- end of session')
        return
      except Exception as e:
        verdict = self.handle_read_exception(e)
        if verdict == "kill-session":
          return
        if verdict == "kill-server":
          Logger.info('Server terminating')
          sys.exit(1)
        # Else keep going
      try:
        if("" == msg):
          Logger.debug(5,'EOF ++ end of session')
          return
        if self.incoming_message(msg) == True:
          return
      except Exception as e:
        Logger.error('Exception in server processing: ' + str(e))
        #print(util.tb_strings())

  def choose_netconf_ver(self, netconf_versions):
    self.netconf_ver = 10
    if 11 in netconf_versions:
      self.netconf_ver = 11
    #print('Using NETCONF protocol version {}'.format(self.netconf_ver))

  def read_msg_10(self):
    chunk_size = 10000
    while True:
      time.sleep(.5)
      next_chunk = self.channel.recv(chunk_size)
      if next_chunk:
        self.indata += next_chunk
      else:
        Logger.debug(8, f"Message10 EOF")
        msg = self.indata
        self.indata = ""
        return msg
      if len(self.indata):
        Logger.debug(8, f"Reading message10, indata size so far {len(self.indata)}", payload=self.indata)
      eom = self.indata.find(self.delimiter10)
      if eom >= 0:
        msg = self.indata[:eom]
        self.indata = self.indata[eom+len(self.delimiter10):]
        Logger.debug(8, f"Message10 complete. Size {len(msg)}, remaining in indata {len(self.indata)}")
        return msg

  def read_msg_11(self):
    chunk_size = 10000
    max_header_len = 15
    frame_len = -1
    msg = b""
    while True:
      Logger.debug(8,f'Read data, indata queue length {len(self.indata)} bytes')
      if frame_len >= 0: # We know the frame length
        # Read frame body until frame_len bytes available
        len_indata = len(self.indata)
        if len_indata >= frame_len: # We have the entire frame
          msg += self.indata[:frame_len]
          self.indata = self.indata[frame_len:]
          frame_len = -1
        else: # We got one more chunk of the frame, but not the entire frame
          msg += self.indata
          frame_len -= len_indata
          self.indata = self.channel.recv(chunk_size)
          if self.indata == b"":
            return b""
      if frame_len < 0: # Have not the frame length header yet
        nl0 = self.indata.find(b"\n")
        nl1 = self.indata.find(b"\n", nl0 + 1)
        Logger.debug(9, f"Header nl0={nl0}, nl1={nl1}, h={self.indata[1] if len(self.indata) >= 2 else None}")
        if nl0 == 0 and nl1 > nl0 and nl1 <= max_header_len and self.indata[1] == ord(b'#'): # Found header
          frame_len_str = self.indata[2:nl1]
          next_frame_start = nl1 + 1
          self.indata = self.indata[next_frame_start:]
          if frame_len_str == b"#": # We got the entire message
            return msg
          try:
            frame_len = int(frame_len_str.decode('utf-8'))
          except:
            Logger.warning(f'Framing error, invalid frame length value: """{frame_len_str}"""')
            return b""
        else:
          if (nl0 == 0 and nl1 > nl0) or (len(self.indata) > max_header_len):
            # Definitely should have a complete header, something is wrong
            Logger.warning(f'Framing error, invalid frame header: """{self.indata[:self.logging_peek_length]}"""')
            return b""
          # No header in sight, better read some more
          data = self.channel.recv(chunk_size)
          self.indata += data
          if data == b"":
            return b""

  # Callback
  def read_msg(self, netconf_ver=0):
    if netconf_ver == 0:
      netconf_ver = self.netconf_ver
    if netconf_ver == 11:
      msg = self.read_msg_11()
    else:
      msg = self.read_msg_10()
    try:
      if isinstance(msg, bytes):
        decoded_msg = msg.decode("utf-8")
      else:
        decoded_msg = msg
      Logger.debug(8,'Received {len(decoded_msg)} byte message: """{decoded_msg[:self.logging_peek_length]}"""')
    except Exception as e:
      Logger.warning(f"Could not UTF-8 decode message", payload=msg)
      raise
    return decoded_msg

  def send_msg_hook(self, msg):
      if "<hello" in msg:
          return msg.replace("&", "&amp;")
      return msg

  def send_msg_msgid_hook(self, msg, msg_id):
      if msg_id == 0:
          msg_id = self.msg_id
      return msg.format(msg_id)

  def send_msg(self, msg, msg_id=0, netconf_ver=0):
    msg = self.send_msg_msgid_hook(msg, msg_id)
    msg = self.send_msg_hook(msg)
    chunk_size = 10000
    if netconf_ver == 0:
      netconf_ver = self.netconf_ver
    msg_len = len(msg)
    while msg != "":
      chunk = msg[:chunk_size].encode('utf-8')
      chunk_len = len(chunk)
      Logger.debug(7, f'Sending {chunk_len} bytes', payload=chunk[:self.logging_peek_length])
      if netconf_ver == 11:
        self.channel.send("\n#{}\n".format(chunk_len).encode('utf-8'))
      self.channel.send(chunk)
      msg = msg[chunk_size:]
    if netconf_ver == 11:
      self.channel.send(self.delimiter11)
    if netconf_ver == 10:
      self.channel.send(self.delimiter10)
    Logger.info(f'Total {msg_len} bytes in NC{netconf_ver} message')

#  def parse_msg_id(self, message):
#        # Expect occasional malformed XML, so let's do this the crude way
#        rpc_begin   = message.find("<rpc ")
#        rpc_end     = message.find(">", rpc_begin)
#        msgid_begin = message.find("message-id=", rpc_begin, rpc_end)
#        msgid_end   = message.find(" ", msgid_begin, rpc_end)
#        if rpc_begin < 0 or rpc_end < 0 or msgid_begin < 0:
#            return "0"
#        msg_id = ""
#        if msgid_end < 0:
#            msgid_end = rpc_end
#        attr_len = 11
#        msg_id = message[msgid_begin+attr_len:msgid_end].replace("'","").replace('"','')
#        return msg_id

  # Callback
  def handle_read_exception(self, e):
        print('Exception on channel: ' + str(e))
        print(util.tb_strings())
        return 'kill-session'

if __name__ == '__main__':
    main()
