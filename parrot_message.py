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
    self.message_id = "Unknown"

  def match(self, xml_match_str):
    def match_nodes(matchpoint, payloadpoint):
      def matching_tags(matchtag, payloadtag):
        mpos = matchtag.find("}")
        if mpos != -1:
          # If matchtag has namespace, namespaces and tags have to match
          Logger.debug(5, f'NS matching_tags({matchtag}, {payloadtag})')
          return matchtag == payloadtag
        ppos = payloadtag.find("}")
        if ppos != -1:
          # If matchtag has no namespace, only tags have to match
          Logger.debug(5, f'NO matching_tags({matchtag}, {payloadtag})')
          return matchtag == payloadtag[ppos+1:]
        # If neither has namespace, tags have to match
        Logger.debug(5, f'NE matching_tags({matchtag}, {payloadtag})')
        return matchtag == payloadtag
      Logger.debug(5, f'1 match_nodes_t({matchpoint}, {payloadpoint})')
      if matching_tags(matchpoint.tag, payloadpoint.tag):
        for mch in matchpoint: # must match all
          Logger.debug(5, f'3 Trying match {mch}')
          one_match = False
          for pch in payloadpoint: # needs to match one
            Logger.debug(5, f'4 Trying payload {pch}')
            if match_nodes(mch, pch):
              Logger.debug(5, f'M match_nodes_t({mch}, {pch}) = True')
              one_match = True
              break
          if not one_match:
            Logger.debug(5, f'O match_nodes_t({matchpoint}, {payloadpoint}) = False')
            return False
        Logger.debug(5, f'N match_nodes_t({matchpoint}, {payloadpoint}) = True')
        return True
      Logger.debug(5, f'E match_nodes_t({matchpoint}, {payloadpoint}) = False')
      return False
    match_root = ET.fromstring(f'''<parrot-root>{xml_match_str}</parrot-root>''')
    payload_root = ET.fromstring(f'''<parrot-root>{self.payload['xml_text']}</parrot-root>''')
    if match_nodes(match_root, payload_root):
      return True
    return False
