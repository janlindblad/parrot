#!/usr/bin/env python3
#
# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

import sys, os, getopt, traceback, pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from parrot_server_netconf import NETCONF_Server
from parrot_log import Logger
from parrot_builder import Parrot_Builder

class Parrot:
  class NETCONF_Parrot(NETCONF_Server):
    def __init__(self):
      super().__init__()
      self.template = None

    def set_template(self, template):
      self.template = template

    def reply(self, incoming_message):
      try:
        response_msg = self.template.render(
          request = incoming_message,
          message_id = incoming_message.get_message_id(),
          session_id = "4711",#FIXME str(self.session_id),
        )
        return response_msg.strip()
      except Exception as ex:
        Logger.fatal(f"Template rendering error, {self.template}, {incoming_message.get_xml_text()}: {ex}")

  def __init__(self):
    self.server = None

  def run(self, host, port, parrot_file):
    Logger.info(f"Parroting {parrot_file}")
    try:
      parrot_path = pathlib.Path(parrot_file)
      env = Environment(
        loader=FileSystemLoader([parrot_path.parent], followlinks=True),
        autoescape=select_autoescape(['xml'])
      )

      self.server.set_template(env.get_template(str(parrot_path.name)))
      self.server.set_host_port(host, port)
      self.server.serve()
    except Exception as e:
      traceback.print_exc()
      Logger.fatal(f"Top level exception: {str(e)}")

  def run_command_line(self, sys_argv=sys.argv):
    def usage(sys_argv):
      print(f'{sys_argv[0]} --netconf=[host:]port parrot-file.xml')
    verbosity = 4
    host = "localhost"
    port = 8888
    template_dirs = []
    trace_files = []
    parrot_file = None
    try:
      opts, args = getopt.getopt(sys_argv[1:],"hd:vt:m:",
        ["help", "debug=", "verbose", "netconf=", "template-dir="])
    except getopt.GetoptError:
      usage(sys_argv)
      sys.exit(2)
    for opt, arg in opts:
      if opt in ('-h', '--help'):
        usage(sys_argv)
        sys.exit()
      elif opt in ("--netconf"):
        self.server = Parrot.NETCONF_Parrot()
        if ":" in arg:
          (host, port_str) = arg.split(":")
          port = int(port_str)
        else:
          port = int(arg)
      elif opt in ("-t", "--template-dir"):
        template_dirs += [arg]
      elif opt in ("-d", "--debug"):
        verbosity = int(arg)
      elif opt in ("-m", "--make-parrot"):
        trace_files += [arg]
      elif opt in ("-v", "--verbose"):
        verbosity += 1
      else:
        Logger.fatal(f'Unknown option "{opt}".')
        sys.exit(2)

    for trace_file_name in trace_files:
      parrot_file = Parrot_Builder.from_trace_file(trace_file_name)

    if not parrot_file:
      if len(args) != 1:
        usage(sys_argv)
        Logger.fatal(f"{len(args)} parrot files given.", code=2)
      parrot_file = args[0]

    if not self.server:
      usage(sys_argv)
      Logger.fatal(f"{len(args)} server specified.", code=2)


    Logger.set_verbosity(verbosity)

    self.run(host, port, parrot_file)

if ( __name__ == "__main__"):
  Parrot().run_command_line()
