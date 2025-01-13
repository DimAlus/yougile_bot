import json
import traceback
from typing import Tuple, List
from time import strftime, gmtime

from config import config
from bot import send_message


def add_exception(mess: Tuple[str], where: str, traceback: str):
  exc = json.dumps({
    "time": strftime("%Y-%m-%d %H:%M:%S", gmtime()),
    "message": mess,
    "where": where,
    "traceback": traceback,
  })
  send_message(exc, "errors")
  with open(config["log"]["filename"], "a", encoding="UTF-8") as f:
    f.write(exc + "\n")


def exception_logger(func, last_exception: List[int] = [0]):
  def wrapper(*args, **kwargs):
    try:
      res = func(*args, **kwargs)
      return res
    except Exception as ex:
      if last_exception[0] != id(ex):
        add_exception(ex.args, func.__name__, "\n".join(traceback.format_tb(ex.__traceback__)))
        last_exception[0] = id(ex)
      raise
  return wrapper

