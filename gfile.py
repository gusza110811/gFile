import keyboard
import psutil
import os
import time
import sys
import subprocess
from ansi import *

class App:
    def __init__(self):
        self.ansiSupport = True
        self.itemIdx = 0
        self.cwd = os.getcwd()
        self.items = []
        terminal = psutil.Process(os.getppid()).name().lower()
        if os.name == "nt" and "cmd.exe" in terminal: # just one of the many possibility of no ansi support
            self.ansiSupport = False

        return

    def render(self):
        buffer = ""
        buffer += "In "+self.cwd+(CLEARTOEND if self.ansiSupport else "")+"\n"
        for idx, item in enumerate(self.items):
            buffer += RESET
            length = len(buffer.splitlines()[-1].replace(RESET,"").replace(GRAY_BG,"")) + len(item) + 2
            if length > os.get_terminal_size().columns:
                buffer += "\n"
            if idx == self.itemIdx:
                if self.ansiSupport:
                    buffer += GRAY_BG
                else:
                    buffer += "> "
            if self.ansiSupport:
                if os.path.isfile(item):
                    buffer += BRIGHT_WHITE
                elif os.path.isdir(item):
                    buffer += BRIGHT_BLUE
            buffer += "'"+item+"'"+RESET+"   "
        buffer += "\n"
        if self.ansiSupport: buffer = CLEAR+GRAY + buffer
        else: os.system("cls")
        print(buffer,end="",flush=True)

        return
    
    def update_path(self,path):
        self.itemIdx = 0
        os.chdir(path)
        self.cwd = os.getcwd()
        self.items = os.listdir(self.cwd)

    def main(self):
        self.items = os.listdir(self.cwd)

        def nothing(key):return

        def left():
            self.itemIdx = (self.itemIdx-1) % len(self.items)
        def right():
            self.itemIdx = (self.itemIdx+1) % len(self.items)
        def up():
            self.itemIdx = (self.itemIdx-5) % len(self.items)
        def down():
            self.itemIdx = (self.itemIdx+5) % len(self.items)

        def enter():
            print(CLEAR,end="",flush=True)
            target = self.items[self.itemIdx]
            if os.path.isdir(target):
                self.update_path(target)

        def esc():
            self.update_path("..")
        
        def handler(event):
            clear_stdin()
            if event.event_type != keyboard.KEY_DOWN:
                return

            name = event.name
            if name == "left":left()
            elif name == "right":right()
            elif name == "up":up()
            elif name == "down": down()

            elif name == "enter":enter()
            elif name == "esc": esc()

        keyboard.hook(handler)

        while 1:
            self.render()

            key = keyboard.read_key()

            if key == "q":
                clear_stdin()
                sys.exit()

        return

def clear_stdin():
    try:
        if os.name == "nt":
            import msvcrt

            while msvcrt.kbhit():
                msvcrt.getch()
        elif os.name == "posix":
            import select

            stdin, _, _ = select.select([sys.stdin], [], [], 0)
            if stdin:
                if sys.stdin.isatty():
                    from termios import TCIFLUSH, tcflush

                    tcflush(sys.stdin.fileno(), TCIFLUSH)
                else:
                    while sys.stdin.read(1024):
                        pass
    except ImportError:
        pass

if __name__ == "__main__":

    app = App()
    app.main()