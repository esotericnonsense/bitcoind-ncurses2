# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import curses
import asyncio

from macros import MIN_WINDOW_SIZE


class View(object):
    """ Handles basic operations for the central views. """
    def __init__(self):
        self._pad = None
        self._visible = False

        self._nettotals_history = []

        self._window_size = MIN_WINDOW_SIZE

    def _clear_init_pad(self):
        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(20, 100)

    def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 8 or maxx < 3:
            return # Can't do it

        self._pad.refresh(0, 0, 4, 0, min(maxy-3, maxy-2), min(maxx-1, 100))

    async def _draw_if_visible(self):
        if self._visible:
            await self._draw()

    async def on_mode_change(self, newmode):
        if newmode != self._mode_name:
            self._visible = False
            return

        self._visible = True
        await self._draw_if_visible()

    async def on_window_resize(self, y, x):
        # All of the current views assume an x width of 100.
        self._window_size = (y, x)
        await self._draw_if_visible()
