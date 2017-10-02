# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import datetime
import time
import math
import curses
import asyncio

import view


class PeersView(view.View):
    _mode_name = "peers"

    def __init__(self):
        self._peerinfo = None  # raw data from getpeerinfo

        super().__init__()

    async def _draw(self):
        self._clear_init_pad()

        if self._peerinfo:
            po = self._peerinfo

            self._pad.addstr(0, 1, "Node IP              Version                                    Recv      Sent        Time   Height", curses.A_BOLD + curses.color_pair(5))

            window_height = 20
            offset = 0
            for index in range(offset, offset+window_height):
                # TODO: replace this hack with real scrolling.
                if index > 15 and index < len(po):
                    self._pad.addstr(1+index-offset, 1, "<some peers were omitted>")
                    break

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

    async def on_peerinfo(self, key, obj):
        try:
            self._peerinfo = obj["result"]
        except KeyError:
            return

        await self._draw_if_visible()
