# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import datetime
# import math
import curses
import asyncio
# from decimal import Decimal

from macros import MIN_WINDOW_SIZE


class BlockStore(object):
    def __init__(self, client):
        self._client = client

        self._lock = asyncio.Lock()

        self._blocks = {}  # hash -> raw block (full details)

    async def get_block(self, blockhash):
        with await self._lock:
            try:
                return self._blocks[blockhash]
            except KeyError:
                # TODO: handle error if the block doesn't exist at all.
                j = await self._client.request("getblock", [blockhash])
                self._blocks[blockhash] = j["result"]
                return j["result"]

    async def get_previousblockhash(self, blockhash):
        with await self._lock:
            try:
                return self._blocks[blockhash]["previousblockhash"]
            except KeyError:
                raise


class BlockView(object):
    def __init__(self, blockstore):
        self._blockstore = blockstore

        self._pad = None

        self._visible = False

        self._hash = None  # currently browsed hash.

        self._window_size = MIN_WINDOW_SIZE

    def _draw(self, block):
        # TODO: figure out window width etc.

        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(20, 100)

        CGREEN = curses.color_pair(1)
        CCYAN = curses.color_pair(2)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD

        if block:
            #self._pad.addstr(0, 1, "height: " + str(block["height"]).zfill(6) + "    (J/K: browse, HOME/END: quicker, L: latest, G: seek)", CBOLD)
            self._pad.addstr(0, 1, "Height: {}".format(block["height"]), CBOLD)
            self._pad.addstr(0, 30, "Hash: {}".format(block["hash"]), CBOLD)
            self._pad.addstr(1, 28, "Merkle: {}".format(block["merkleroot"]), CBOLD)
            self._pad.addstr(1, 1, "Size: {} bytes".format(block["size"]), CBOLD)
            self._pad.addstr(2, 1, "Weight: {} WU".format(block["weight"]), CBOLD)
            self._pad.addstr(2, 28, "Difficulty: {:,d}".format(int(block["difficulty"])), CBOLD)
            self._pad.addstr(2, 70, "Timestamp: {}".format(
                datetime.datetime.utcfromtimestamp(block["time"]).isoformat(timespec="seconds")
            ), CBOLD)
            self._pad.addstr(3, 81, "Version: 0x{}".format(block["versionHex"]), CBOLD)

        self._draw_pad_to_screen()

    def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 8 or maxx < 3:
            return # Can't do it

        self._pad.refresh(0, 0, 4, 0, min(maxy-3, 24), min(maxx-1, 100))

    async def draw(self):
        block = None
        if self._hash:
            block = await self._blockstore.get_block(self._hash)

        self._draw(block)

    async def on_bestblockhash(self, key, obj):
        try:
            bestblockhash = obj["result"]
        except KeyError:
            return

        # If we have no browse hash, set it to the best.
        if self._hash is None:
            self._hash = bestblockhash

            if self._visible:
                await self.draw()

    async def on_mode_change(self, newmode):
        if newmode != "block":
            self._visible = False
            return

        self._visible = True
        await self.draw()

    async def on_window_resize(self, y, x):
        # At the moment we ignore the x size and limit to 100.
        self._window_size = (y, x)
        if self._visible:
            await self.draw()
