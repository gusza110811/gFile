#!/bin/python3
import pynput
import os
import sys
import termios
import subprocess
from ansi import *
import re

class App:
    def __init__(self):
        self.ansiSupport = True
        self.itemIdx = 0
        self.cwd = os.getcwd()
        self.items = []

        self.distanceToNextLn = []

        self.HELP = "Arrow keys to select items\n\
Esc to move to parent directory\n\
Enter to move into the selected directory\n\
Q to quit\n\
C to start shell here\n\
H to show this message"

        return

    def render(self):

        buffer = ""
        buffer += CLEAR+"\n"+GRAY+ "In "+self.cwd+CLEARTOEND+"\n"
        items = 0
        padding = max([len(item) for item in self.items])
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
            buffer += "'"+item+"'"+RESET+(" "*(padding-len(item)))
        distanceToNextLn = distanceToNextLn + ([items]*items)
        self.distanceToNextLn = distanceToNextLn.copy()

        buffer += "\n"
        print(buffer,end="",flush=True)

        return
    
    def update_path(self,path):
        prevdir = os.getcwd().split("/")[-1]
        os.chdir(path)
        self.cwd = os.getcwd()
        self.items = os.listdir(self.cwd)
        self.items.sort()
        self.items.insert(0,"..")
        try:
            self.itemIdx = self.items.index(prevdir)
        except ValueError:
            self.itemIdx = 0

    def quit(self):
        self.listener.stop()

    def main(self):
        self.update_path(os.getcwd())

        def left():
            self.itemIdx = (self.itemIdx-1) % len(self.items)
        def right():
            self.itemIdx = (self.itemIdx+1) % len(self.items)

        def up():
            try:
                dist = self.distanceToNextLn[self.itemIdx-self.distanceToNextLn[self.itemIdx]] % len(self.distanceToNextLn)
                self.itemIdx = (self.itemIdx-dist) % len(self.items)
            except IndexError:
                left()
        def down():
            try:
                self.itemIdx = (self.itemIdx+self.distanceToNextLn[self.itemIdx]) % len(self.items)
            except IndexError:
                right()

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
                if os.name != "nt":
                    termios.tcflush(sys.stdin, termios.TCIFLUSH)
                shell = os.environ['SHELL']
                if not shell:
                    if os.name == "nt":
                        shell = "c:/windows/system32/cmd.exe"
                    else:
                        shell = "/bin/sh"
                subprocess.call([shell])

            if name == "h":
                print(self.HELP)

        print(CLEAR)
        self.render()
        self.listener = pynput.keyboard.Listener(handler)
        self.listener.start()
        try:
            self.listener.join()
        except KeyboardInterrupt:
            self.quit()
        print(CLEAR)
        if os.name != "nt":
            termios.tcflush(sys.stdin, termios.TCIFLUSH)

        return

if __name__ == "__main__":

    app = App()
    app.main()