"""
This code is created cuz, the default python Thread doesn't support to kill it, the only way is ending the whole process
which is not ideal for this app
this helps to overcome that :)

!!! This is NOT MY CODE !!!

This code is copied from GFG and reworked to match my coding practice
src=https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
"""

__all__ = ['KillableThread']

import sys
import time
from threading import Thread


class KillableThread(Thread):
    def __init__(self, *args, **keywords):
        # Thread.__init__(self, *args, **keywords)
        super().__init__(*args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run  # NOQA, cuz adding it to __init__ cause error
        self.run = self.__run         # NOQA
        Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):  # NOQA
        if event == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):  # NOQA
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


if __name__ == '__main__':
    def test_func():
        while True:
            print('thread running')
            time.sleep(10)
    
    t1 = KillableThread(target=test_func)
    t1.start()
    time.sleep(2)
    t1.kill()
    t1.join()
    if not t1.is_alive():
        print('thread killed')
    else:
        print('Its alive :o')
    while True:
        print('This is fun')
        time.sleep(0.1)
