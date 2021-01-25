# Parrot
# Keeps repeating the messages you train it with over and over
#
# The parrot is intended to be used as a device simulator when you need
# exact control over the messages returned, in order to trigger specific
# situations in a NETCONF client.
#
# (C) 2021 Cisco Systems
# Written by Jan Lindblad <jlindbla@cisco.com>

import sys, traceback, datetime, threading

class Logger:
  peek_length = 120
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
  def _emit_msg(level, prompt, message, payload=None):
    def peek(level, payload):
      if Logger.verbosity_level >= 7:
        if isinstance(payload, bytes):
          payload = "b'''"+payload.decode('utf-8')+"'''"
        return payload
      if Logger.verbosity_level >= 5:
        if isinstance(payload, bytes):
          peekstr = "b'"+payload.decode('utf-8')
        else:
          peekstr = "'"+str(payload)
        if len(peekstr) > Logger.peek_length:
          peekstr = peekstr[:Logger.peek_length]
          peekstr += "..."
        peekstr = peekstr.replace('\n',' ')
        return peekstr+"'"
      return None
    if Logger.verbosity_level >= level:
      now = str(datetime.datetime.now())[:-4]
      print(f"{now} {prompt}: {message}")
    if payload:
      peekstr = peek(level, payload)
      if peekstr:
        Logger._emit_msg(level, "----", peekstr, None)
      #Logger.show_trace()
    if Logger.verbosity_level >= 10:
      for th in threading.enumerate():
        print(f"....    {th}")

  @staticmethod
  def debug(level, message, payload=None):
    Logger._emit_msg(level, f"DBG{level}", message, payload)

  @staticmethod
  def fatal(message, code=9, payload=None):
    Logger._emit_msg(1, "****: Parrot Fatal Error", message, payload)
    sys.exit(code)

  @staticmethod
  def error(message, payload=None):
    Logger._emit_msg(2, "****: Parrot Error", message, payload)

  @staticmethod
  def warning(message, payload=None):
    Logger._emit_msg(3, "WARN", message, payload)

  @staticmethod
  def info(message, payload=None):
    Logger._emit_msg(4, "INFO", message, payload)
