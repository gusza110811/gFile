#!/bin/env python3
import os, sys, subprocess
import termios, tty
import threading
import re
from collections import deque
import waiting
import filetype

esc = "\x1b["

HOME = f"{esc}H"
CLEAR = f"{esc}H{esc}2J"
CLEARLINE = f"{esc}2K"
CLEARTOEND = f"{esc}0K"
CLEARFROM1 = f"{esc}1K"
CLEARBELOW = f"{esc}0J"
CURSORUP = f"{esc}1A"

RESET = f"{esc}0m"
MAGENTA = f"{esc}35m"
RED = f"{esc}31m"
GREEN = f"{esc}32m"
BLUE = f"{esc}34m"
CYAN = f"{esc}36m"
WHITE = f"{esc}37m"
GRAY = f"{esc}90m"
GRAY_BG = f"{esc}100m"

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
        self.itemCol = 0
        self.itemRow = 0
        self.cwd = os.getcwd()
        self.items = []
        self.items2d:list[list] = []
        self.hide_hidden = True

        self.running = True

        self.busy_wait = True

        self.listener = Key_Listener()

        self.distanceToNextLn = []

        self.HELP = """
Arrow keys/H/J/K/L
        move selection
Esc     move to parent directory
Enter/space
        move into the selected directory
Q       quit
C       start shell here
T       start new terminal here
F       open selection with xdg-open
G       select the first item
Shift+G select the last item
Shift+H show this message
"""

        return

    def render(self):

        buffer = ""
        try:
            buffer += HOME+"\n"+GRAY+self.cwd+"/"+ WHITE+self.items2d[self.itemRow][self.itemCol]+CLEARTOEND+"\n"
        except IndexError:
            buffer += HOME+"\n"+GRAY+self.cwd+"/?"+CLEARTOEND+"\n"
        max_item_len = min(os.get_terminal_size().columns // 5,80)
        olditems2d = self.items2d
        self.items2d = []
        rowi = 0
        coli = 0
        row = []
        padding = min(max([len(item) for item in self.items]),max_item_len)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        for idx, item in enumerate(self.items):
            buffer += RESET
            length = len(ansi_escape.sub("",buffer.splitlines()[-1])) + len(item) + 3 + padding-len(item)

            if length > os.get_terminal_size().columns:
                rowi += 1
                coli = 0
                self.items2d.append(row)
                row = []
                buffer += "\n"
                row.append(item)
            else:
                coli += 1
                row.append(item)
            try:
                if olditems2d[self.itemRow][self.itemCol] == item:
                    buffer += GRAY_BG
            except IndexError:
                pass
            if self.ansiSupport:
                if os.path.isdir(item):
                    buffer += BLUE
                elif filetype.is_image(item) or filetype.is_video(item):
                    buffer += MAGENTA
                elif os.access(item,os.X_OK):
                    buffer += GREEN
                elif os.path.islink(item):
                    buffer += CYAN
                elif filetype.is_archive(item):
                    buffer += RED
                else:
                    buffer += WHITE
            if len(item) > max_item_len:
                item = item[:max_item_len-3]+"..."
            buffer += "'"+item+"'"+RESET+(" "*(padding-len(item)))
        
        if row:
            self.items2d.append(row)

        buffer += "\n"
        print(buffer,end="",flush=True)

        return
    
    def update_path(self,path=None):
        print(CLEAR,end="")
        prevdir = os.getcwd().split("/")[-1]
        try:
            if path: os.chdir(path)
        except OSError:
            return
        self.cwd = os.getcwd()
        self.items = os.listdir(self.cwd)

        def find_nested(item_name):
            for idx, row in enumerate(self.items2d):
                try:
                    return idx, row.index(item_name)
                except ValueError:
                    pass
            
            raise ValueError(f"{item_name} not found")

        if self.items:
            if self.hide_hidden:
                self.items = [name for name in self.items if not name.startswith(".")]

            self.items.sort()

        self.items.insert(0,"..")
        self.items.insert(0,".")
        try:
            self.itemRow, self.itemCol = find_nested(prevdir)
        except ValueError:
            try:
                self.itemRow, self.itemCol = 0, min(2,len(self.items2d[self.itemRow])-1)
            except IndexError:
                self.itemRow, self.itemCol = 0, 2

    def quit(self,message:str="Exit"):
        print("\x1b[?25h\x1b[?1049l", end="")  # leave alt screen
        print(message)
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.orig)
        sys.exit()

    def main(self, path:str):
        self.update_path(path)
        self.orig = termios.tcgetattr(sys.stdin.fileno())

        def left():
            self.itemCol = (self.itemCol-1) % len(self.items2d[self.itemRow])
        def right():
            self.itemCol = (self.itemCol+1) % len(self.items2d[self.itemRow])

        def up():
            if self.itemRow == 0:
                return
            self.itemRow -= 1

        def down():
            if self.itemRow == len(self.items2d)-1:
                return
            self.itemRow += 1
            self.itemCol = min(self.itemCol, len(self.items2d[self.itemRow]) - 1)
        def top():
            self.itemIdx = 2
        def bottom():
            self.itemIdx = len(self.items)-1

        def enter():
            print(CLEAR,end="",flush=True)
            target = self.items2d[self.itemRow][self.itemCol]
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
                self.running = False
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
                target = self.items2d[self.itemRow][self.itemCol]
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

        print("\x1b[?1049h\x1b[?25l", end="")  # enter alt screen and hide cursor

        self.listener.start()

        self.render(); self.render() # the reason it needs to render twice on start is quite silly

        try:
            while self.running:
                key = parse()
                print(CLEAR)
                handler(key)
                self.render()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.quit(f"Exit due to unknown error ({e})")
        self.quit()

if __name__ == "__main__":

    app = App()

    try:
        path = sys.argv[1]
    except IndexError:
        path = os.path.expanduser('~')

    app.main(path)