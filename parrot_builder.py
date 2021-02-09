# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

import pathlib, datetime
from parrot_log import Logger

class Parrot_Builder:
  @staticmethod
  def from_trace_file(source_filename):
    parrot_filename = None
    if source_filename.endswith(".trace"):
      parrot_filename = NSO_Trace_Parrot_Builder(source_filename).build()
    if parrot_filename:
      return parrot_filename
    Logger.fatal(f"Parrot Builder, unrecognized trace file type: {source_filename}")


class NSO_Trace_Parrot_Builder:
  inmark = "<<<<in "
  outmark = ">>>>out "
  parrot_hello = '<hello xmlns="parrot"/>'

  def __init__(self, source_filename, target_filename=None):
    self.source_filename = pathlib.Path(source_filename)
    if not target_filename:
      target_filename = source_filename + ".parrot.xml"
    self.target_filename = pathlib.Path(target_filename)
    if not self.source_filename.exists():
      Logger.fatal(f"Parrot Builder, can't find trace file: {source_filename}")
    self.catalog = {}
    self.catalog_meta = {}

  def build(self):
    if self.target_filename.exists():
      source_stat = self.source_filename.stat()
      target_stat = self.target_filename.stat()
      if source_stat.st_mtime <= target_stat.st_mtime:
        Logger.info(f"Parrot Builder, {self.target_filename} up to date")
        return str(self.target_filename)

    with open(self.source_filename, "r") as source_file:
      with open(self.target_filename, "w") as target_file:
        self._make_messages(source_file)
        self._emit_messages(target_file)
    return str(self.target_filename)

  @staticmethod
  def _is_meta_in(text):
    return text.startswith(NSO_Trace_Parrot_Builder.inmark)
  @staticmethod
  def _is_meta_out(text):
    return text.startswith(NSO_Trace_Parrot_Builder.outmark)
  @staticmethod
  def _is_meta(text):
    return NSO_Trace_Parrot_Builder._is_meta_in(text) or NSO_Trace_Parrot_Builder._is_meta_out(text)
  @staticmethod
  def _meta_dir(text):
    if text.startswith("meta:"):
      return "meta"
    elif NSO_Trace_Parrot_Builder._is_meta_in(text):
      return "in"
    elif NSO_Trace_Parrot_Builder._is_meta_out(text):
      return "out"
    return None

  def _make_messages(self, source_file):
    source_lines = source_file.readlines()
    message = ""
    meta = "meta:preamble"
    for line in source_lines:
      if NSO_Trace_Parrot_Builder._is_meta(line):
        self._record_message(message.strip(), meta.strip())
        message = ""
        meta = line
        continue
      else:
        message += line

  def _record_message(self, message, meta):
    # This method should maybe parse the XML properly, but since
    # we also want this to work with potentially malformed XML,
    # it is instead making some assumptions about the XML encoding
    direction = NSO_Trace_Parrot_Builder._meta_dir(meta)
    if not direction:
      Logger.fatal(f"Message meta malformed: {meta}")
    message_id_attr_str = "message-id="
    # Assume first occurrence of message-id is the NETCONF message-id
    pos = message.find(message_id_attr_str)
    if pos >= 0:
      pos += len(message_id_attr_str)
      delimiter = message[pos]
      # Assume message-id value is properly delimited
      if delimiter not in ['"',"'"]:
        Logger.fatal(f"Attribute message-id= malformed (1): {meta}")
      pos += 1
      endpos = message[pos:].find(delimiter)
      # Assume message-id value is at most 100 chars
      if endpos < 0 or endpos > 100:
        Logger.fatal(f"Attribute message-id= malformed (2): {meta}")
      message_id = message[pos:pos+endpos]
      self.catalog[(direction, message_id)] = message
      self.catalog_meta[(direction, message_id)] = meta
      print(f"Recorded message {direction} {message_id} = {message[:40]}...")
    # Assume hello message is not namespaced, and has no redundant whitespace
    elif message.startswith("<hello "):
      self.catalog[(direction, "hello")] = message
      self.catalog_meta[(direction, "hello")] = meta
    elif direction == "meta":
      self.catalog[(direction, meta)] = message
      self.catalog_meta[(direction, meta)] = meta
      pass
    elif not message:
      pass
    else:
      Logger.fatal(f"Message not hello and lacks message-id: {meta}")

  def _emit_messages(self, target_file):
    self.target_file = target_file
    self._emit_header()
    message_ids = list({e[1] for e in self.catalog if isinstance(e, tuple)})
    message_ids.sort()
    #check for hello messages
    #check for balanced responses

    for message_id in message_ids:
      if message_id == "meta:preamble":
        continue
      key = ("out", message_id)
      print(f"Emitting message {key}")
      if key == ("out", "hello"):
        self._emit_out(message_id, NSO_Trace_Parrot_Builder.parrot_hello, "spontaneously sent hello")
      else:
        self._emit_out(message_id, self.catalog[key], self.catalog_meta[key])
      key = ("in", message_id)
      print(f"Emitting message {key}")
      self._emit_in (message_id, self.catalog[key], self.catalog_meta[key])
    self._emit_trailer()

  def _emit_header(self):
    timestamp = datetime.datetime.now().strftime("%d %B %Y %H:%M:%S")
    print(f"""{{# Autogenerated Parrot based on {self.source_filename}, {timestamp}
##
## SELECT VER ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## 
#}}
{{% if request.match('''
<hello/>
''') %}}
<?parrot netconf11?>
{{# CLOSE      ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## 
{{% elif request.match("<rpc><close-session/></rpc>") %}}
<?parrot end-session?>""", file=self.target_file)

  def _emit_trailer(self):
    print(f'''{{# END        ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## #}}
{{% endif %}}
{{# ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## #}}''', 
      file=self.target_file)

  def _emit_out(self, message_id, message, meta):
    print(f"Out {meta} {message_id} {len(message)} chars: {message[:40]}...")
    print(f"""{{# MATCH      ########## ########## ########## ########## ########## ########## ########## ########## ########## ########## ##########
## {meta} #}}
{{% elif request.match('''
{message}
''') %}}""", file=self.target_file)

  def _emit_in(self, message_id, message, meta):
    print(f"In  {meta} {message_id} {len(message)} chars: {message[:40]}...")
    print(f'''{{# SEND       ---------- ---------- ---------- ---------- ---------- ---------- ---------- ---------- ---------- ---------- ----------
## {meta} #}}
{message}''', file=self.target_file)
