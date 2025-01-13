import json
import requests
from typing import Dict, List
from time import sleep
from html import escape as escape_html

from config import config
from logger import exception_logger
from bot import send_message

public_context = {
  "todo": True,
}
_context = {
  "tasks": None,
  "users": {},
  "columns": {},
  "boards": {},
}
_line_break = "\n"


def concat_if(s: str, prefix: str, suffix: str) -> str:
  return f"{prefix}{s}{suffix}" if s else ""


@exception_logger
def query(endpoint: str, params: Dict | None = None):
  res = requests.get(
      url=f"https://ru.yougile.com/api-v2/{endpoint}",
      params=params,
      headers={
        "Authorization": f"Bearer {config['yougile']['token']}",
        "Content-Type": "application/json"
      }
    )
  return res


@exception_logger
def get_data_generator(endpoint: str):
  is_next = True
  offset = 0
  while is_next:
    res = query(endpoint, { "limit": 1000, "offset": offset })
    offset += 1000
    if res.ok:
      data = json.loads(res.text)
      is_next = data["paging"]["next"]
      for tsk in data["content"]:
        yield tsk
    else:
      raise Exception("Request failed!").with_traceback()


@exception_logger
def get_assigned_users(task: Dict) -> List[Dict[str, str]]:
  global _context
  result = []
  if "assigned" in task:
    tsks = [task["assigned"]] if isinstance(task["assigned"], str) else task["assigned"]
    for user in tsks:
      if user not in _context["users"]:
        res = query(f"users/{user}") 
        if res.ok:
          data = json.loads(res.text)
          _context["users"][user] = data
        else:
          print(f"get_assigned_users: Failed read user [{user}]")
      if user in _context["users"]:
        result.append(_context["users"][user])
  return result


@exception_logger
def get_path(task: Dict) -> Dict[str, str]:
  global _context
  if "columnId" not in task:
    return {
      "col_title": "???",
      "board_title": "???",
      "url": "https://ru.yougile.com/team/7d250d600e4c/Forest"
    }
  col = task["columnId"]
  if col not in _context["columns"]:
    res = query(f"columns/{col}")
    if res.ok:
      data = json.loads(res.text)
      _context["columns"][col] = data
    else:
      print(f"get_path: Failed read column [{col}]")

  col_data = _context["columns"][col]


  if col_data["boardId"] not in _context["boards"]:
    res = query(f"boards/{col_data['boardId']}")
    if res.ok:
      data = json.loads(res.text)
      _context["boards"][col_data["boardId"]] = data
    else:
      print(f"get_path: Failed read column [{col}]")

  board_data = _context["boards"][col_data["boardId"]]
  return {
    "col_title": col_data["title"],
    "board_title": board_data["title"],
    "url": f"https://ru.yougile.com/team/7d250d600e4c/Forest/{board_data['title']}"
  }


@exception_logger
def save_boards():
  global _context
  boards: Dict[str, Dict] = {}

  for brd in get_data_generator("boards"):
    boards[brd["id"]] = brd
  
  _context["boards"] = boards


@exception_logger
def save_columns():
  global _context
  columns: Dict[str, Dict] = {}

  for brd in get_data_generator("columns"):
    columns[brd["id"]] = brd
  
  _context["columns"] = columns


@exception_logger
def initialize_context():
  global _context
  save_boards()
  save_columns()
  tasks: Dict[str, Dict] = {}
  for tsk in get_data_generator("tasks"):
    path = get_path(tsk)
    if not path["col_title"].startswith("Идеи") and path["col_title"] != "???":
      tasks[tsk["id"]] = tsk
  
  _context["tasks"] = tasks


@exception_logger
def mes_create_task(task: Dict):
  users = ", ".join([config["users"].get(usr["email"], usr["email"]) for usr in get_assigned_users(task)])
  path = get_path(task)
  send_message(f"""<b>{escape_html(task['title'])}</b>
{concat_if(users, "", _line_break)}
Событие: Задача создана

Местоположение: 
{escape_html(path['board_title'])} -> {escape_html(path['col_title'])}
{escape_html(path['url'])}
""")


@exception_logger
def mes_cancel_task(task: Dict):
  users = ", ".join([config["users"].get(usr["email"], usr["email"]) for usr in get_assigned_users(task)])
  path = get_path(task)
  send_message(f"""<b>{escape_html(task['title'])}</b>
{concat_if(users, "", _line_break)}
Событие: Задача отменена

{escape_html(path['url'])}
""")


@exception_logger
def mes_apply_task(task: Dict):
  users = ", ".join([config["users"].get(usr["email"], usr["email"]) for usr in get_assigned_users(task)])
  path = get_path(task)
  send_message(f"""<b>{escape_html(task['title'])}</b>
{concat_if(users, "", _line_break)}
Событие: Задача выполнена

{escape_html(path['url'])}
""")


@exception_logger
def compare_tasks(old_task: Dict, new_task: Dict):
  o, n = old_task, new_task
  changes = []
  path = get_path(n)
  if (
      (not o.get("completed", False) and n.get("completed", False))  or 
      (o.get("columnId", "") != n.get("columnId", "") and path["col_title"].startswith("Готово"))
  ):
    mes_apply_task(n)
    return
  # if o["title"] != n["title"]:
  #   changes.append(f"Старое название: {escape_html(o['title'])}")
  if set(o.get("assigned", [])) != set(n.get("assigned", [])):
    users = ", ".join([usr["realName"] for usr in get_assigned_users(n)])
    changes.append(f"Текущие исполнители: {users}")
  if o.get("columnId", "") != n.get("columnId", ""):
    changes.append(f"Местоположение:\n{escape_html(path['board_title'])} -> {escape_html(path['col_title'])}")
  
  if len(changes) > 0:
     users = ", ".join([config["users"].get(usr["email"], usr["email"]) for usr in get_assigned_users(n)])

     send_message(f"""<b>{escape_html(n['title'])}</b>
{concat_if(users, "", _line_break)}
Событие: Задача перемещена

Местоположение: 
{escape_html(path['board_title'])} -> {escape_html(path['col_title'])}
{escape_html(path['url'])}
""")
     # {'\n\n'.join(changes)}


@exception_logger
def update():
  global _context
  for tsk in get_data_generator("tasks"):
    path = get_path(tsk)
    if tsk["id"] not in _context["tasks"]:
      if not path["col_title"].startswith("Идеи") and path["col_title"] != "???":
        if path["col_title"].startswith("Готово"):
          mes_apply_task(tsk)
        else:
          mes_create_task(tsk)
        _context["tasks"][tsk["id"]] = tsk
    elif path["col_title"].startswith("Идеи") or path["col_title"] == "???":
      mes_cancel_task(tsk)
      _context["tasks"].pop(tsk["id"])
    else:
      compare_tasks(_context["tasks"][tsk["id"]], tsk)
      _context["tasks"][tsk["id"]] = tsk



@exception_logger
def check_tasks():
  global _context
  if _context["tasks"] is None:
    initialize_context()

  current_interval = config["process"]["check_interval"]
  update_columns_interval = config["process"]["update_columns_interval"]
  while public_context["todo"]:
    sleep(1)
    current_interval -= 1
    update_columns_interval -= 1
    if update_columns_interval < 0:
      save_boards()
      save_columns()
      update_columns_interval = config["process"]["update_columns_interval"]
    if current_interval < 0:
      print("Updating")
      update()
      current_interval = config["process"]["check_interval"]

