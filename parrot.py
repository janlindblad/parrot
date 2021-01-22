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

import sys, os, getopt, traceback
from jinja2 import Environment, FileSystemLoader, select_autoescape
from parrot_server_netconf import NETCONF_Server
from parrot_log import Logger

class Parrot:
  class NETCONF_Parrot(NETCONF_Server):
    def __init__(self):
      super().__init__()
      self.template = None

    def set_template(self, template):
      self.template = template

    def reply(self, incoming_message):
      response_msg = self.template.render(
        request = incoming_message,
        message_id = incoming_message.get_message_id(),
        session_id = "4711",#FIXME str(self.session_id),
      )
      return response_msg

  def __init__(self):
    self.server = None

  def run(self, host, port, parrot_file):
    try:
      env = Environment(
        loader=FileSystemLoader(['parrots'], followlinks=True),
        autoescape=select_autoescape(['xml'])
      )
      self.server.set_template(env.get_template(parrot_file))
      self.server.set_host_port(host, port)
      self.server.serve()
    except Exception as e:
      Logger.fatal(f"Top level exception: {str(e)}")
      #traceback.print_exc()

  def run_command_line(self, sys_argv=sys.argv):
    def usage(sys_argv):
      print(f'{sys_argv[0]} --netconf=[host:]port parrot-file.xml')
    verbosity = 3
    host = "localhost"
    port = 8888
    template_dirs = []
    try:
      opts, args = getopt.getopt(sys_argv[1:],"hd:vt:",
        ["help", "debug=", "verbosity", "netconf=", "template-dir="])
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
      elif opt in ("-v", "--verbosity"):
        verbosity += 1
      else:
        Logger.fatal(f'Unknown option "{opt}".')
        sys.exit(2)

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
