#!/bin/env python3
import os, sys, subprocess
import termios, tty
import threading
from ansi import *
import re
from collections import deque
import waiting

class Key_Listener(threading.Thread):
    def __init__(self, group = None, name = None):
        super().__init__(group, self.listen, name, daemon=True)
        self.buffer = deque()
        self.suspended = False
        self.suspend_accept = False

    def listen(self):
        while 1:
            if self.suspended:
                self.suspend_accept = True
                waiting.wait(lambda: not self.suspended)
            self.buffer.append(sys.stdin.read(1))

    def get(self):
        try:
            return self.buffer.popleft()
        except IndexError:
            return "\0"

    def wait(self):
        waiting.wait(lambda: len(self.buffer) > 0)

        return self.buffer.popleft()

    def busy_wait(self):
        while len(self.buffer) == 0:
            if self.suspended:
                return ""

        return self.buffer.popleft()

    def clear(self):
        self.buffer = deque()
    
    def suspend(self):
        self.suspended = True
        while not self.suspend_accept: pass # make sure the thread suspended
    
    def cont(self):
        self.suspended = False
        self.suspend_accept = False

class App:
    def __init__(self):
        self.ansiSupport = True
        self.itemIdx = 0
        self.cwd = os.getcwd()
        self.items = []
        self.hide_hidden = True

        self.running = True

        self.busy_wait = True

        self.listener = Key_Listener()

        self.distanceToNextLn = []

        self.HELP = """
Arrow keys/H/J/K/L
        move selection
Esc     move to parent directory
Enter   move into the selected directory
Q       quit
C       start shell here
T       start new terminal here
F       open selection with xdg-open
G       select the first item (excluding . and ..)
SHIFT+G select the last item
SHIFT+H show this message
"""

        return

    def render(self):

        buffer = ""
        buffer += CLEAR+"\n"+GRAY+self.cwd+"/"+ WHITE+self.items[self.itemIdx]+CLEARTOEND+"\n"
        max_item_len = min(os.get_terminal_size().columns // 6,80)
        items = 0
        padding = min(max([len(item) for item in self.items]),max_item_len)
        distanceToNextLn = []
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        for idx, item in enumerate(self.items):
            buffer += RESET
            length = len(ansi_escape.sub("",buffer.splitlines()[-1])) + len(item) + 3 + padding-len(item)
            if length > os.get_terminal_size().columns:
                distanceToNextLn = distanceToNextLn + ([items]*items)
                items = 0
                buffer += "\n"
            if idx == self.itemIdx:
                buffer += GRAY_BG
            if self.ansiSupport:
                if os.path.isfile(item):
                    buffer += BRIGHT_WHITE
                elif os.path.isdir(item):
                    buffer += BRIGHT_BLUE
            items += 1
            if len(item) > max_item_len:
                item = item[:max_item_len-3]+GRAY+"..."
            buffer += "'"+item+"'"+RESET+(" "*(padding-len(item)))
        distanceToNextLn = distanceToNextLn + ([items]*items)
        self.distanceToNextLn = distanceToNextLn.copy()

        buffer += "\n"
        print(buffer,end="",flush=True)

        return
    
    def update_path(self,path=None):
        prevdir = os.getcwd().split("/")[-1]
        if path: os.chdir(path)
        self.cwd = os.getcwd()
        self.items = os.listdir(self.cwd)

        if self.items:
            if self.hide_hidden:
                self.items = [name for name in self.items if not name.startswith(".")]

            self.items.sort()

        self.items.insert(0,"..")
        self.items.insert(0,".")
        try:
            self.itemIdx = self.items.index(prevdir)
        except ValueError:
            self.itemIdx = min(2, len(self.items)-1)

    def quit(self,message:str="Exit"):
        print("\x1b[?25h\x1b[?1049l", end="")  # leave alt screen
        print(message)
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.orig)
        sys.exit()

    def main(self, path:str):
        self.update_path(path)
        self.orig = termios.tcgetattr(sys.stdin.fileno())

        def left():
            self.itemIdx = (self.itemIdx-1) % len(self.items)
        def right():
            self.itemIdx = (self.itemIdx+1) % len(self.items)

        def up():
            try:
                dist = self.distanceToNextLn[self.itemIdx-self.distanceToNextLn[self.itemIdx]] % len(self.distanceToNextLn)
                self.itemIdx = max(self.itemIdx-dist, 0)
            except IndexError:
                left()
        def down():
            try:
                dist = self.distanceToNextLn[self.itemIdx]
                self.itemIdx = min(self.itemIdx+dist, len(self.items)-1)
            except IndexError:
                right()
        def top():
            self.itemIdx = 2
        def bottom():
            self.itemIdx = len(self.items)-1

        def enter():
            print(CLEAR,end="",flush=True)
            target = self.items[self.itemIdx]
            if os.path.isdir(target):
                self.update_path(target)
        
        def toggle_hidden():
            self.hide_hidden = not self.hide_hidden
            self.update_path()
        
        def handler(name:str):

            if name == "LEFT":left()
            elif name == "DOWN":down()
            elif name == "UP":up()
            elif name == "RIGHT":right()
            elif name == "TOP":top()
            elif name == "BOTTOM":bottom()

            elif name == "DOT":toggle_hidden()
            elif name == "ENTER":enter()
            elif name == "PARENT":self.update_path("..")

            self.render()
            if name == "QUIT":
                self.quit("Quit")
            if name == "SHELL":
                self.busy_wait = False
                self.listener.suspend()
                shell = os.environ['SHELL']
                if not shell:
                    shell = "/bin/sh"
                subprocess.run([shell])
                self.listener.cont()
                self.busy_wait = True

            if name == "TERMINAL":
                term = os.environ['TERMINAL']
                if not term:
                    print("$TERMINAL is not set")
                try:
                    subprocess.Popen([term])
                except OSError:
                    print("Failed to start terminal")

            if name == "OPEN":
                target = self.items[self.itemIdx]
                subprocess.Popen(["xdg-open", target])

            if name == "HELP":
                print(self.HELP)
        
        def parse():
            listener = self.listener
            if self.busy_wait:
                pre = listener.busy_wait()
            else:
                pre = listener.wait()
            output = "\0"

            if pre == "\x1b":
                pre += listener.get() + listener.get()

            if pre == "\x1b[A" or pre == "k":
                output = "UP"
            elif pre == "\x1b[B" or pre == "j":
                output = "DOWN"
            elif pre == "\x1b[C" or pre == "l":
                output = "RIGHT"
            elif pre == "\x1b[D" or pre == "h":
                output = "LEFT"

            elif pre == "a":
                output = "PARENT"
            elif pre == "G":
                output = "BOTTOM"
            elif pre == "g":
                output = "TOP"
            elif pre == ".":
                output = "DOT"
            elif pre == " " or pre == "\n":
                output = "ENTER"
            
            elif pre == "q":
                output = "QUIT"
            elif pre == "s":
                output = "SHELL"
            elif pre == "t":
                output = "TERMINAL"
            elif pre == "f":
                output = "OPEN"
            elif pre == "H":
                output = "HELP"

            return output

        stdin = sys.stdin

        tty.setcbreak(stdin.fileno())

        #print("\x1b[?1049h\x1b[?25l", end="")  # enter alt screen and hide cursor

        self.listener.start()

        try:
            self.render()
            while self.running:
                key = parse()
                print(CLEAR)
                self.render()
                handler(key)
        except KeyboardInterrupt:
            pass
        self.quit()

        return

if __name__ == "__main__":

    app = App()

    try:
        path = sys.argv[1]
    except IndexError:
        path = os.path.expanduser('~')

    app.main(path)