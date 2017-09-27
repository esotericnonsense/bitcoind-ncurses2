# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import datetime
import time
import math
import curses
import asyncio

from macros import MIN_WINDOW_SIZE

class PeersView(object):
    def __init__(self):
        self._pad = None
        self._visible = False
        self._peerinfo = None  # raw data from getpeerinfo

        self._window_size = MIN_WINDOW_SIZE

    def draw(self):
        # TODO: figure out window width etc.

        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(20, 100) # y, x

        if self._peerinfo:
            po = self._peerinfo

            self._pad.addstr(0, 1, "Node IP              Version                                    Recv      Sent        Time   Height", curses.A_BOLD + curses.color_pair(5))

            window_height = 20
            offset = 0
            for index in range(offset, offset+window_height):
                if index < len(po):
                    peer = po[index]

                    condition = (index == offset+window_height-1) and (index+1 < len(state['peerinfo']))
                    condition = condition or ( (index == offset) and (index > 0) )

                    if condition:
                        # scrolling up or down is possible
                        self._pad.addstr(1+index-offset, 3, "...")

                    else:
                        if peer['inbound']:
                            self._pad.addstr(1+index-offset, 1, 'I')

                        elif 'syncnode' in peer:
                            if peer['syncnode']:
                                # syncnodes are outgoing only
                                self._pad.addstr(1+index-offset, 1, 'S')

                        addr_str = peer['addr'].replace(".onion","").replace(":8333","").replace(":    18333","").strip("[").strip("]")

                        # truncate long ip addresses (ipv6)
                        addr_str = (addr_str[:17] + '...') if len(addr_str) > 20 else addr_str

                        self._pad.addstr(1+index-offset, 1, addr_str)
                        self._pad.addstr(1+index-offset, 22,
                            peer['subver'][1:40][:-1]
                        )

                        mbrecv = "% 7.1f" % ( float(peer['bytesrecv']) / 1048576 )
                        mbsent = "% 7.1f" % ( float(peer['bytessent']) / 1048576 )

                        self._pad.addstr(1+index-offset, 60, mbrecv + 'MB')
                        self._pad.addstr(1+index-offset, 70, mbsent + 'MB')

                        timedelta = int(time.time() - peer['conntime'])
                        m, s = divmod(timedelta, 60)
                        h, m = divmod(m, 60)
                        d, h = divmod(h, 24)

                        time_string = ""
                        if d:
                            time_string += ("%d" % d + "d").rjust(3) + " "
                            time_string += "%02d" % h + ":"
                        elif h:
                            time_string += "%02d" % h + ":"
                        time_string += "%02d" % m + ":"
                        time_string += "%02d" % s

                        self._pad.addstr(1+index-offset, 79, time_string.rjust(12))

                        if 'synced_headers' in peer:
                          self._pad.addstr(1+index-offset, 93, str(peer['synced_headers']).rjust(7)    )

        self._draw_pad_to_screen()

    def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 8 or maxx < 3:
            return # Can't do it

        self._pad.refresh(0, 0, 4, 0, min(maxy-3, 24), min(maxx-1, 100))

    async def on_peerinfo(self, key, obj):
        try:
            self._peerinfo = obj["result"]
        except KeyError:
            return

        if self._visible:
            self.draw()

    async def on_mode_change(self, newmode):
        if newmode != "peers":
            self._visible = False
            return

        self._visible = True
        self.draw()

    async def on_window_resize(self, y, x):
        # At the moment we ignore the x size and limit to 100.
        self._window_size = (y, x)
        if self._visible:
            await self.draw()
