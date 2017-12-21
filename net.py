# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import math
import curses
import asyncio

import view


class NetView(view.View):
    _mode_name = "net"

    def __init__(self):
        self._nettotals_history = []

        super().__init__()

    async def _draw(self):
        self._clear_init_pad()

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

        if not self._nettotals_history or len(deltas) < 1:
            await self._draw_no_chart()
        else:
            await self._draw_chart(deltas)

        self._draw_pad_to_screen()

    async def _draw_no_chart(self):
        CRED = curses.color_pair(3)
        CBOLD = curses.A_BOLD
        self._pad.addstr(0, 1, "no network information yet", CRED + CBOLD)
        self._pad.addstr(1, 1, "please wait a few seconds...", CRED)

    async def _draw_chart(self, deltas):
        ph, pw = 20, 100
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

            up_str = "Up: {: 9.2f}kB/s".format(deltas[-1][0]/1024).rjust(10)
            down_str = "Down: {: 9.2f}kB/s".format(deltas[-1][1]/1024).rjust(10)
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

    async def on_nettotals(self, key, obj):
        try:
            self._nettotals_history.append(obj["result"])
        except KeyError:
            pass

        # Avoid memory leak.
        if len(self._nettotals_history) > 500:
            self._nettotals_history = self._nettotals_history[:300]

        await self._draw_if_visible()
