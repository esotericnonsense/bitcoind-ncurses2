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
        self._bestblockhash = None

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

    async def get_nextblockhash(self, blockhash):
        with await self._lock:
            try:
                return self._blocks[blockhash]["nextblockhash"]
            except KeyError:
                raise

    async def get_previousblockhash_n(self, blockhash, n):
        if n <= 0:
            raise TypeError

        # This is based on height.
        with await self._lock:
            try:
                block = self._blocks[blockhash]
            except KeyError:
                raise

        if block["height"] < n:
            raise KeyError

        j = await self._client.request("getblockhash", [block["height"] - n])

        try:
            return j["result"]
        except KeyError:
            raise

    async def get_nextblockhash_n(self, blockhash, n):
        if n <= 0:
            raise TypeError

        # This is based on height.
        with await self._lock:
            try:
                block = self._blocks[blockhash]
            except KeyError:
                raise

            try:
                bestblock = self._blocks[self._bestblockhash]
            except KeyError:
                raise

        if bestblock["height"] - block["height"] < n:
            raise KeyError

        j = await self._client.request("getblockhash", [block["height"] + n])

        try:
            return j["result"]
        except KeyError:
            raise

    async def on_bestblockhash(self, blockhash):
        with await self._lock:
            self._bestblockhash = blockhash
            # TODO: if the previous block exists, update its' nextblockhash

    async def get_bestblockhash(self):
        with await self._lock:
            if self._bestblockhash is None:
                raise KeyError

            return self._bestblockhash

class BlockView(object):
    def __init__(self, blockstore):
        self._blockstore = blockstore

        self._pad = None

        self._visible = False

        self._hash = None  # currently browsed hash.

        self._window_size = MIN_WINDOW_SIZE

    def _draw(self, block, bestblockhash):
        # TODO: figure out window width etc.

        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(20, 100)

        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD

        if block:
            self._pad.addstr(0, 59, "[J/K: browse, HOME/END: quicker, L: best]", CYELLOW)

            self._pad.addstr(0, 1, "Time {}".format(
                datetime.datetime.utcfromtimestamp(block["time"]).isoformat(timespec="seconds")
            ), CBOLD)
            self._pad.addstr(0, 31, "Height {}".format(block["height"]), CBOLD)

            self._pad.addstr(1, 1, "Size {} bytes".format(block["size"]), CBOLD)
            self._pad.addstr(2, 1, "Weight {} WU".format(block["weight"]), CBOLD)
            self._pad.addstr(3, 1, "Diff {:,d}".format(int(block["difficulty"])), CBOLD)
            self._pad.addstr(4, 1, "Version 0x{}".format(block["versionHex"]), CBOLD)

            self._pad.addstr(1, 31, "Hash {}".format(block["hash"]), CBOLD)
            if "previousblockhash" in block:
                self._pad.addstr(2, 31, "Prev {}".format(block["previousblockhash"]), CBOLD)
            else:
                self._pad.addstr(2, 60, "genesis block!", CBOLD + CRED)

            if "nextblockhash" in block:
                self._pad.addstr(3, 31, "Next {}".format(block["nextblockhash"]), CBOLD)
            elif block["hash"] == bestblockhash:
                self._pad.addstr(3, 60, "best block!", CBOLD + CGREEN)

            self._pad.addstr(4, 31, "Root {}".format(block["merkleroot"]), CBOLD)

        self._draw_pad_to_screen()

    def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 8 or maxx < 3:
            return # Can't do it

        self._pad.refresh(0, 0, 4, 0, min(maxy-3, 24), min(maxx-1, 100))

    async def _select_previous_block(self):
        if self._hash is None:
            return # Can't do anything

        try:
            self._hash = await self._blockstore.get_previousblockhash(self._hash)
        except KeyError:
            return # Can't do anything

        await self.draw()

    async def _select_next_block(self):
        if self._hash is None:
            return # Can't do anything

        try:
            self._hash = await self._blockstore.get_nextblockhash(self._hash)
        except KeyError:
            return # Can't do anything

        await self.draw()

    async def _select_previous_block_n(self, n):
        if self._hash is None:
            return # Can't do anything

        try:
            self._hash = await self._blockstore.get_previousblockhash_n(self._hash, n)
        except KeyError:
            return # Can't do anything

        await self.draw()

    async def _select_next_block_n(self, n):
        if self._hash is None:
            return # Can't do anything

        try:
            self._hash = await self._blockstore.get_nextblockhash_n(self._hash, n)
        except KeyError:
            return # Can't do anything

        await self.draw()

    async def _select_best_block(self):
        if self._hash is None:
            return # Can't do anything

        try:
            self._hash = await self._blockstore.get_bestblockhash()
        except KeyError:
            return # Can't do anything

        await self.draw()

    async def draw(self):
        if not self._visible:
            return

        block = None
        bestblockhash = None
        if self._hash:
            block = await self._blockstore.get_block(self._hash)
            bestblockhash = await self._blockstore.get_bestblockhash()

        self._draw(block, bestblockhash)

    async def on_bestblockhash(self, key, obj):
        try:
            bestblockhash = obj["result"]
        except KeyError:
            return

        await self._blockstore.on_bestblockhash(bestblockhash)

        # If we have no browse hash, set it to the best.
        if self._hash is None:
            self._hash = bestblockhash

        # Redraw so that we know if it's the best
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

    async def handle_keypress(self, key):
        assert self._visible

        if key.lower() == "j":
            await self._select_previous_block()
            return None

        if key.lower() == "k":
            await self._select_next_block()
            return None

        if key == "KEY_HOME":
            await self._select_previous_block_n(1000)
            return None

        if key == "KEY_END":
            await self._select_next_block_n(1000)
            return None

        if key.lower() == "l":
            await self._select_best_block()
            return None

        return key
