from time import sleep, gmtime, strftime
from threading import Thread

from task_checker import check_tasks, public_context

if __name__ == "__main__":
  thread = Thread(target=check_tasks)
  thread.start()

  try:
    while True:
      sleep(10)
      if not thread.is_alive():
        print("Thread dead! Creating new thread.")
        thread = Thread(target=check_tasks)
        thread.start()
  except:
    public_context["todo"] = False
    print("Canceling")
