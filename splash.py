# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import curses
import asyncio

from macros import MIN_WINDOW_SIZE, DEFAULT_MODE

import time

splash_array = [
    " BB            BB                                   BB    ",
    " BB       BB   BB    BBBB    BBBB   BB  BB BB       BB    ",
    " BBBBB        BBBB  BB     BB   BB      BBB BB   BBBBB    ",
    " BB   BB  BB   BB   BB     BB   BB  BB  BB  BB  BB  BB    ",
    " BBB  BB  BB   BB   BB     BB   BB  BB  BB  BB  BB  BB    ",
    " BB BBB   BB    BB   BBBB    BBBB   BB  BB  BB    BBBB    ",
    "                                                          ",
    "                               ---------------------------",
    "                                n   c   u   r   s   e   s ",
    "                               ---------------------------",
]
width = len(splash_array[0])
height = len(splash_array)

class SplashView(object):
    def __init__(self, set_mode_callback):
        self._set_mode_callback = set_mode_callback # ModeHandler

        self._pad = None

        self._window_size = MIN_WINDOW_SIZE

    async def draw(self, nosplash):
        if nosplash:
            await self._end_splash(nosplash)
            return

        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(20, 100)

        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        for x in range(len(splash_array[0])):
            for y in range(len(splash_array)):
                if splash_array[y][x] == "B":
                    if y < 7:
                        self._pad.addstr(y+1, x, " ", CGREEN + CREVERSE)
                    else:
                        self._pad.addstr(y+1, x, " ", CRED + CREVERSE)
                elif splash_array[y][x] != " ":
                    self._pad.addstr(y+1, x, splash_array[y][x], CRED + CBOLD)
                y += 1
            await self._draw_pad_to_screen()
            time.sleep(0.01)

        await asyncio.sleep(0.5)
        time.sleep(0.5)
        await self._end_splash(nosplash)

    async def _end_splash(self, nosplash):
        if not nosplash:
            self._pad.clear()
            await self._draw_pad_to_screen()

        await self._set_mode_callback(DEFAULT_MODE)

    async def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < height+1 or maxx < width+1:
            return # Can't do it

        t = (maxy-height)//2
        l = (maxx-width)//2
        self._pad.refresh(0, 0, t, l, t+height, l+width)

    async def on_window_resize(self, y, x):
        # This should prevent the splash from crashing
        #   if there's a resize during the draw operations.
        self._window_size = (y, x)
