import os

esc = "\x1b["
if os.name == "nt":
    os.system('')

HOME = f"{esc}H"
CLEAR = f"{esc}H{esc}2J"
CLEARLINE = f"{esc}2K"
CLEARTOEND = f"{esc}0K"
CLEARFROM1 = f"{esc}1K"
CLEARBELOW = f"{esc}0J"

RESET = f"{esc}0m"
BLUE = f"{esc}34m"
BRIGHT_BLUE = f"{esc}94m"
WHITE = f"{esc}37m"
BRIGHT_WHITE = f"{esc}97m"
GRAY = f"{esc}90m"
GRAY_BG = f"{esc}100m"