# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

import xml.etree.ElementTree as ET
from parrot_log import Logger

class Message:
  def __init__(self, xml_text=None):
    self.payload = {}

  def get_message_id(self):
    return "unknown"

  def match(self, xml_text):
    raise Exception("Abstract Message can't match")

class XML_Message(Message):
  def __init__(self, xml_text):
    super().__init__()
    self.payload['xml_text'] = xml_text

  def get_message_id(self):
    root = self.get_xml_etree()
    rpc = root[0]
    attrs = rpc.attrib
    message_id = attrs.get('message-id')
    return message_id

  def get_xml_text(self):
    return self.payload['xml_text']

  def get_xml_etree(self):
    if not self.payload.get('xml_etree'):
      self.payload['xml_etree'] = ET.fromstring(
        f'''<parrot-root>{self.get_xml_text()}</parrot-root>''')
    return self.payload.get('xml_etree')

  def match(self, xml_match_str):
    def match_nodes(matchpoint, payloadpoint):
      def matching_tags(matchtag, payloadtag):
        mpos = matchtag.find("}")
        if mpos != -1:
          # If matchtag has namespace, namespaces and tags have to match
          Logger.debug(8, f'Match NS matching_tags({matchtag}, {payloadtag})')
          return matchtag == payloadtag
        ppos = payloadtag.find("}")
        if ppos != -1:
          # If matchtag has no namespace, only tags have to match
          Logger.debug(8, f'Match NO matching_tags({matchtag}, {payloadtag})')
          return matchtag == payloadtag[ppos+1:]
        # If neither has namespace, tags have to match
        Logger.debug(8, f'Match NE matching_tags({matchtag}, {payloadtag})')
        return matchtag == payloadtag
      Logger.debug(8, f'Match 1 match_nodes_t({matchpoint}, {payloadpoint})')
      if matching_tags(matchpoint.tag, payloadpoint.tag):
        for mch in matchpoint: # must match all
          Logger.debug(8, f'Match 3 Trying match {mch}')
          one_match = False
          for pch in payloadpoint: # needs to match one
            Logger.debug(8, f'Match 4 Trying payload {pch}')
            if match_nodes(mch, pch):
              Logger.debug(8, f'Match M match_nodes_t({mch}, {pch}) = True')
              one_match = True
              break
          if not one_match:
            Logger.debug(8, f'Match O match_nodes_t({matchpoint}, {payloadpoint}) = False')
            return False
        Logger.debug(8, f'Match N match_nodes_t({matchpoint}, {payloadpoint}) = True')
        return True
      Logger.debug(8, f'Match E match_nodes_t({matchpoint}, {payloadpoint}) = False')
      return False
    match_root = ET.fromstring(f'''<parrot-root>{xml_match_str}</parrot-root>''')
    if match_nodes(match_root, self.get_xml_etree()):
      Logger.debug(5, f"Incoming message template match '{xml_match_str}'")
      return True
    return False
