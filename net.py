# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import math
import curses
import asyncio

from macros import MIN_WINDOW_SIZE


class NetView(object):
    def __init__(self):
        self._pad = None

        self._visible = False

        self._nettotals_history = []

        self._window_size = MIN_WINDOW_SIZE

    async def _draw(self, deltas):
        ph, pw = 20, 100

        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(ph, pw)

        plot_height = (ph-3) // 2
        plot_offset = plot_height
        chart_offset = 13
        chart_width = pw - chart_offset

        CGREEN = curses.color_pair(1)
        CCYAN = curses.color_pair(2)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        if deltas:
            if len(deltas) > chart_width:
                deltas = deltas[-chart_width:]

            up_str = "Up: {: 9.2f}kB/s".format(deltas[-1][1]/1024).rjust(10)
            down_str = "Down: {: 9.2f}kB/s".format(deltas[-1][0]/1024).rjust(10)
            total_str = "Total: {: 9.2f}kB/s".format((deltas[-1][0] + deltas[-1][1])/1024).rjust(10)
            self._pad.addstr(ph-2, pw-62, up_str, CBOLD + CCYAN)
            self._pad.addstr(ph-2, pw-42, down_str, CBOLD + CGREEN)
            self._pad.addstr(ph-2, pw-20, total_str, CBOLD)

            max_up = max(delta[0] for delta in deltas)
            max_down = max(delta[1] for delta in deltas)
            max_total = max(max_up, max_down)

            if max_total > 0:
                if max_up > 0:
                    height = int(math.ceil((1.0 * plot_height * max_up) / max_total))
                    self._pad.addstr(plot_offset-height, 1, "{: 5.0f}kB/s".format(max_up//1024).rjust(10), CBOLD) 
                if max_down > 0:
                    height = int(math.ceil((1.0 * plot_height * max_down) / max_total))
                    self._pad.addstr(plot_offset-1+height, 1, "{: 5.0f}kB/s".format(max_down//1024).rjust(10), CBOLD) 

                for i, delta in enumerate(deltas):
                    if i > chart_width:
                        break

                    height = int(math.ceil((1.0 * plot_height * deltas[i][0]) / max_total))
                    for y in range(0, height):
                        self._pad.addstr(plot_offset-1-y, i+12, " ", CCYAN + CREVERSE)

                    height = int(math.ceil((1.0 * plot_height * deltas[i][1]) / max_total))
                    for y in range(0, height):
                        self._pad.addstr(plot_offset+y, i+12, " ", CGREEN + CREVERSE)

        self._draw_pad_to_screen()

    def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 8 or maxx < 3:
            return # Can't do it

        self._pad.refresh(0, 0, 4, 0, min(maxy-3, maxy-2), min(maxx-1, 100))

    async def draw(self):
        if self._visible:
            deltas = []
            if self._nettotals_history:
                hist = self._nettotals_history
                i = 1
                while i < len(hist):
                    prev = hist[i-1]
                    current = hist[i]
                    seconds = (current["timemillis"] - prev["timemillis"]) / 1000
                    if seconds <= 0:
                        continue
                    up = current["totalbytessent"] - prev["totalbytessent"]
                    down = current["totalbytesrecv"] - prev["totalbytesrecv"]

                    deltas.append(
                        (up/seconds, down/seconds),
                    )

                    i += 1

            await self._draw(deltas)

    async def on_nettotals(self, key, obj):
        try:
            self._nettotals_history.append(obj["result"])
        except KeyError:
            pass

        # Avoid memory leak.
        if len(self._nettotals_history) > 500:
            self._nettotals_history = self._nettotals_history[:300]

        await self.draw()

    async def on_mode_change(self, newmode):
        if newmode != "net":
            self._visible = False
            return

        self._visible = True
        await self.draw()

    async def on_window_resize(self, y, x):
        # At the moment we ignore the x size and limit to 100.
        self._window_size = (y, x)
        await self.draw()
