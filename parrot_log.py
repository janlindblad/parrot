# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

import sys, traceback

class Logger:
  trace_level = 0
  verbosity_level = 3
  # 0 total silence, 1 fatal, 2 errors, 3 warnings
  # 4 info
  # 5 communication events
  # 6 abbreviated traffic
  # 7 full traffic
  # 8 internal processing

  @staticmethod
  def set_verbosity(level):
    Logger.verbosity_level = level

  @staticmethod
  def set_trace(level):
    Logger.trace_level = level

  @staticmethod
  def trace(level, message):
    pass

  @staticmethod
  def show_trace():
    pass#traceback.print_exc()

  @staticmethod
  def debug(level, message, payload=None):
    if Logger.verbosity_level >= level:
      print(f"DBG{level}: {message}")
    if payload and Logger.verbosity_level >= level+2:
      print(f"{str(payload)}")
    elif payload and Logger.verbosity_level >= level+1:
      pstr = str(payload)
      maxlen = 40
      print(f'     "{pstr[:maxlen]}{"..." if len(pstr) > maxlen else ""}"')
  
  @staticmethod
  def fatal(msg, code=9, payload=None):
    if Logger.verbosity_level >= 1:
      print(f"*** Parrot Fatal Error: {msg}")
      Logger.show_trace()
    sys.exit(code)

  @staticmethod
  def error(msg, payload=None):
    if Logger.verbosity_level >= 2:
      print(f"*** Parrot Error: {msg}")
      Logger.show_trace()

  @staticmethod
  def warning(msg, payload=None):
    if Logger.verbosity_level >= 3:
      print(f"WARN: {msg}")

  @staticmethod
  def info(msg, payload=None):
    if Logger.verbosity_level >= 4:
      print(f"INFO: {msg}")
