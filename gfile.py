import pynput
import os
import sys
import termios
import subprocess
from ansi import *

class App:
    def __init__(self):
        self.ansiSupport = True
        self.itemIdx = 0
        self.cwd = os.getcwd()
        self.items = []

        self.running = True

        self.clearPending = False

        self.distanceToNextLn = []

        self.HELP = "Arrow keys to select items\n\
            Esc to move to parent directory\n\
            Enter to move into the selected directory\n\
            Q to quit\n\
            C to start shell here\n\
            H to show this message"

        return

    def render(self):
        if self.clearPending:
            print(CLEAR)
            self.clearPending = False

        buffer = ""
        buffer += HOME+"\n"+GRAY+ "In "+self.cwd+CLEARTOEND+"\n"
        items = 0
        maxlength = max([len(item) for item in self.items])

        for idx, item in enumerate(self.items):
            buffer += RESET
            length = len(buffer.splitlines()[-1].replace(RESET,"").replace(GRAY_BG,"").replace(BRIGHT_BLUE,"").replace(BRIGHT_WHITE,"").replace(RESET,"")) + len(item) + 2
            if length > os.get_terminal_size().columns:
                self.distanceToNextLn = self.distanceToNextLn + ([items]*items)
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
            buffer += "'"+item+"'"+RESET+(" "*(maxlength-len(item))+" ")


        buffer += "\n"
        print(buffer,end="",flush=True)

        return
    
    def update_path(self,path):
        print(CLEAR)
        self.itemIdx = 0
        os.chdir(path)
        self.cwd = os.getcwd()
        self.items = os.listdir(self.cwd)
    
    def quit(self):
        self.running = False

    def main(self):
        self.items = os.listdir(self.cwd)

        def left():
            self.itemIdx = (self.itemIdx-1) % len(self.items)
        def right():
            self.itemIdx = (self.itemIdx+1) % len(self.items)
        def up():
            self.itemIdx = (self.itemIdx-self.distanceToNextLn[self.itemIdx]) % len(self.items)
        def down():
            self.itemIdx = (self.itemIdx+self.distanceToNextLn[self.itemIdx]) % len(self.items)

        def enter():
            print(CLEAR,end="",flush=True)
            target = self.items[self.itemIdx]
            if os.path.isdir(target):
                self.update_path(target)

        def esc():
            self.update_path("..")
        
        def handler(key):
            keys = pynput.keyboard.Key

            name = key
            if name == keys.left:left()
            elif name == keys.right:right()
            elif name == keys.up:up()
            elif name == keys.down: down()

            elif name == keys.enter:enter()
            elif name == keys.esc: esc()

            try:
                name = key.char
            except AttributeError:
                name = None

            self.render()
            if name == "q":
                self.quit()
            if name == "c":
                termios.tcflush(sys.stdin,termios.TCIFLUSH)
                shell = os.environ['SHELL']
                subprocess.call([shell])
                self.clearPending = True

            if name == "h":
                print(self.HELP)
                self.clearPending = True

        self.listener = pynput.keyboard.Listener(handler)
        self.listener.start()
        print(CLEAR)
        self.render()

        try:
            while self.running:
                pass
        except KeyboardInterrupt:
            quit()

        termios.tcflush(sys.stdin,termios.TCIFLUSH)
        os.system(f"cd {self.cwd}")
        self.listener.stop()

        return

if __name__ == "__main__":

    app = App()
    app.main()