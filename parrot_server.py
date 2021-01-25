# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

from parrot_message import Message, XML_Message
from parrot_log import Logger

class YANG_Server:
  sessions = []
  class Session:
    prev_session_id = 0

  def __init__(self):
    YANG_Server.Session.prev_session_id += 1
    self.session_id = YANG_Server.Session.prev_session_id
    self.prev_message_id = 0

  def serve(self):
    pass
    self.listen()
    new_session = self.start_session()

  def start_session(self):
    new_session = YANG_Server.Session()
    self.sessions += [new_session]
    return new_session

  def incoming_message(self, text):
    Logger.trace(1,text)
    Logger.debug(6, f'Incoming message {len(text)} bytes', payload=text)
    new_text = self.receive_raw_message(text)
    reply_msg = self.receive_message(new_text)
    return self.process_instructions(reply_msg)

  def process_instructions(self, reply_msg):
    def split_processing_instructions(reply_msg):
      instructions = []
      pi_start_marker = '<?parrot '
      pi_end_marker = '?>'
      while True:
        pi_start = reply_msg.find(pi_start_marker)
        if pi_start < 0:
          break
        pi_end = reply_msg[pi_start:].find(pi_end_marker)
        if pi_end < 0:
          return ('bad-processing-instruction', reply_msg[pi_start:pi_start+20])
        pi = reply_msg[pi_start+len(pi_start_marker):pi_end]
        if pi_start:
          instructions += [('send', reply_msg[:pi_start])]
        reply_msg = reply_msg[pi_end+len(pi_end_marker):]
        cmd = pi.split(" ")[0]
        data = pi[len(cmd)+1:]
        instructions += [(cmd, data)]
      if reply_msg:
        instructions += [('send', reply_msg)]
      if not instructions:
        instructions = [('empty-response', None)]
      return instructions

    instructions = split_processing_instructions(reply_msg)
    end_session = False
    for (cmd, data) in instructions:
      if cmd == "send":
        Logger.debug(6, f'Sending {len(data)} bytes', payload=data)
        self.send_message(data)
      elif cmd == "ignore":
        Logger.debug(5, f'Not sending any response')
      elif cmd == "netconf11":
        Logger.debug(5, f'Switching to NETCONF 1.1')
        self.choose_netconf_ver([11])
      elif cmd == "netconf10":
        Logger.debug(5, f'Switching to NETCONF 1.0')
        self.choose_netconf_ver([10])
      elif cmd == "empty-response":
        Logger.warning(f'Template did not provide any response. Ending the session.')
        end_session = True
      elif cmd == "end-session":
        Logger.info(f'Ending session')
        end_session = True
      else:
        Logger.error(f'Unknown processing instruction "{cmd}" in template. Ending the session.')
        end_session = True
    return end_session

  def receive_raw_message(self, text):
    text = text.replace('<?xml version="1.0" encoding="UTF-8"?>','') ##FIXME
    return text

  def receive_message(self, text):
    raise Exception("Abstract YANG_Server can't receive any message")

  def send_message(self, message):
    self.send_msg(message)
    return message

  def reply(self, incoming_message):
    raise Exception("Abstract YANG_Server can't reply to any message")
