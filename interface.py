# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import curses

from macros import MIN_WINDOW_SIZE


def init_curses():
    window = curses.initscr()
    curses.noecho()
    curses.curs_set(0)

    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    window.timeout(50)
    window.keypad(1)

    return window


def end_curses():
    curses.nocbreak()
    curses.endwin()


def check_min_window_size(y, x):
    if (y < MIN_WINDOW_SIZE[0]):
        raise Exception("Window is too small, {} < {}".format(y, MIN_WINDOW_SIZE[0]))

    if (x < MIN_WINDOW_SIZE[1]):
        raise Exception("Window is too small, {} < {}".format(x, MIN_WINDOW_SIZE[1]))
