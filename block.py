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

        # Pre-fetch it if necessary and update the previous block
        # TODO: think about the locking here.
        block = await self.get_block(blockhash)
        with await self._lock:
            try:
                prevblock = self._blocks[block["previousblockhash"]]
            except KeyError:
                return

            if "nextblockhash" in prevblock:
                if prevblock["nextblockhash"] == blockhash:
                    return

                raise Exception("BlockStore does not handle re-orgs")

            prevblock["nextblockhash"] = blockhash

    async def get_bestblockhash(self):
        with await self._lock:
            if self._bestblockhash is None:
                raise KeyError

            return self._bestblockhash

class BlockView(object):
    def __init__(self, blockstore, txidsetter, modesetter):
        self._blockstore = blockstore

        self._txidsetter = txidsetter
        self._modesetter = modesetter

        self._pad = None

        self._visible = False

        self._hash = None  # currently browsed hash.
        self._selected_tx = None # (index, blockhash)
        self._tx_offset = None # (offset, blockhash)

        self._window_size = MIN_WINDOW_SIZE

    async def _set_hash(self, newhash):
        # TODO: lock?
        self._hash = newhash
        self._selected_tx = (0, newhash)
        self._tx_offset = (0, newhash)

    async def _draw_block(self, block, bestblockhash):
        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD

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

    async def _draw_transactions(self, block, bestblockhash):
        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        self._pad.addstr(6, 36, "Transactions: {}".format(
            len(block["tx"])), CBOLD)
        self._pad.addstr(6, 68, "[UP/DOWN: browse, ENTER: select]".format(
            len(block["tx"])), CYELLOW)

        if self._selected_tx is None or self._tx_offset is None:
            # Shouldn't happen
            raise Exception

        if self._selected_tx[1] != block["hash"] or self._tx_offset[1] != block["hash"]:
            # Shouldn't happen
            raise Exception

        offset = self._tx_offset[0]
        if offset > 0:
            self._pad.addstr(7, 36, "... ^ ...", CBOLD)
        if offset < len(block["tx"]) - 9:
            self._pad.addstr(17, 36, "... v ...", CBOLD)
        for i, txid in enumerate(block["tx"]):
            if i < offset: # this is lazy
                continue
            if i > offset+8: # this is lazy
                break

            if i == self._selected_tx[0] and self._hash == self._selected_tx[1]:
                self._pad.addstr(8+i-offset, 36, "{}".format(txid), CBOLD + CREVERSE)
            else:
                self._pad.addstr(8+i-offset, 36, "{}".format(txid))


    async def _draw(self, block, bestblockhash):
        # TODO: figure out window width etc.

        if self._pad is not None:
            self._pad.clear()
        else:
            self._pad = curses.newpad(20, 100)


        if block:
            await self._draw_block(block, bestblockhash)
            await self._draw_transactions(block, bestblockhash)

        await self._draw_pad_to_screen()

    async def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 8 or maxx < 3:
            return # Can't do it

        self._pad.refresh(0, 0, 4, 0, min(maxy-3, 24), min(maxx-1, 100))

    async def _select_previous_transaction(self):
        if self._hash is None:
            return # Can't do anything

        if self._selected_tx == None or self._selected_tx[1] != self._hash:
            return # Can't do anything

        if self._tx_offset == None or self._tx_offset[1] != self._hash:
            return # Can't do anything

        if self._selected_tx[0] == 0:
            return # At the beginning already.

        if self._selected_tx[0] == self._tx_offset[0]:
            self._tx_offset = (self._tx_offset[0] - 1, self._tx_offset[1])

        self._selected_tx = (self._selected_tx[0] - 1, self._selected_tx[1])

        await self.draw()

    async def _select_next_transaction(self):
        if self._hash is None:
            return # Can't do anything

        if self._selected_tx == None or self._selected_tx[1] != self._hash:
            return # Can't do anything

        if self._tx_offset == None or self._tx_offset[1] != self._hash:
            return # Can't do anything

        try:
            block = await self._blockstore.get_block(self._hash)
        except KeyError:
            return # Can't do anything

        if self._selected_tx[0] == len(block["tx"]) - 1:
            return # At the end already

        if self._selected_tx[0] == self._tx_offset[0] + 8:
            self._tx_offset = (self._tx_offset[0] + 1, self._tx_offset[1])

        self._selected_tx = (self._selected_tx[0] + 1, self._selected_tx[1])

        await self.draw()

    async def _enter_transaction_view(self):
        if self._hash is None:
            return # Can't do anything

        if self._selected_tx == None or self._selected_tx[1] != self._hash:
            return # Can't do anything

        if self._tx_offset == None or self._tx_offset[1] != self._hash:
            return # This shouldn't matter, but skip anyway

        try:
            block = await self._blockstore.get_block(self._hash)
        except KeyError:
            return # Can't do anything

        txid = block["tx"][self._selected_tx[0]]

        await self._txidsetter(txid)
        await self._modesetter("transaction")

    async def _select_previous_block(self):
        if self._hash is None:
            return # Can't do anything

        try:
            newhash = await self._blockstore.get_previousblockhash(self._hash)
        except KeyError:
            return # Can't do anything

        await self._set_hash(newhash)
        await self.draw()

    async def _select_next_block(self):
        if self._hash is None:
            return # Can't do anything

        try:
            newhash = await self._blockstore.get_nextblockhash(self._hash)
        except KeyError:
            return # Can't do anything

        await self._set_hash(newhash)
        await self.draw()

    async def _select_previous_block_n(self, n):
        if self._hash is None:
            return # Can't do anything

        try:
            newhash = await self._blockstore.get_previousblockhash_n(self._hash, n)
        except KeyError:
            return # Can't do anything

        await self._set_hash(newhash)
        await self.draw()

    async def _select_next_block_n(self, n):
        if self._hash is None:
            return # Can't do anything

        try:
            newhash = await self._blockstore.get_nextblockhash_n(self._hash, n)
        except KeyError:
            return # Can't do anything

        await self._set_hash(newhash)
        await self.draw()

    async def _select_best_block(self):
        if self._hash is None:
            return # Can't do anything

        try:
            newhash = await self._blockstore.get_bestblockhash()
        except KeyError:
            return # Can't do anything

        await self._set_hash(newhash)
        await self.draw()

    async def draw(self):
        if not self._visible:
            return

        block = None
        bestblockhash = None
        if self._hash:
            block = await self._blockstore.get_block(self._hash)
            bestblockhash = await self._blockstore.get_bestblockhash()

        await self._draw(block, bestblockhash)

    async def on_bestblockhash(self, key, obj):
        try:
            bestblockhash = obj["result"]
        except KeyError:
            return

        await self._blockstore.on_bestblockhash(bestblockhash)

        # If we have no browse hash, set it to the best.
        if self._hash is None:
            newhash = bestblockhash
            await self._set_hash(newhash)

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

        if key == "KEY_UP":
            await self._select_previous_transaction()
            return None

        if key == "KEY_DOWN":
            await self._select_next_transaction()
            return None

        if key == "KEY_RETURN" or key == "\n":
            await self._enter_transaction_view()
            return None

        if key.lower() == "l":
            await self._select_best_block()
            return None

        return key
