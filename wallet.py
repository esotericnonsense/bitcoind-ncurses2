# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import datetime
import curses
import asyncio

import view
from util import isoformatseconds

class WalletView(view.View):
    _mode_name = "wallet"

    def __init__(self, txidsetter, modesetter):
        self._txidsetter = txidsetter
        self._modesetter = modesetter

        self._wallet = None
        self._tx_offset = None  # (index, hash of wallet)
        self._selected_tx = None  # (index, hash of wallet)

        super().__init__()

    async def _draw_wallet(self, wallet):
        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        if "transactions" in wallet:
            offset = self._tx_offset[0]

            self._pad.addstr(0, 1, "Transactions: {}".format(
                len(wallet["transactions"])), CBOLD)
            self._pad.addstr(0, 68, "[UP/DOWN: browse, ENTER: select]", CYELLOW)

            if offset > 0:
                self._pad.addstr(1, 25, "... ^ ...", CBOLD)

            if offset < len(wallet["transactions"]) - 11:
                self._pad.addstr(19, 25, "... v ...", CBOLD)

            for i, tx in enumerate(wallet["transactions"]):
                if i < offset:
                    continue
                if i > offset+5:
                    break

                color = CGREEN if tx["amount"] >= 0 else CRED
                # if i == self._selected_tx[0] and self._hash == self._selected_tx[1]:
                if i == self._selected_tx[0]:
                    color += CBOLD + CREVERSE
                    # hackerino
                    self._pad.addstr(2+((i-offset)*3), 1, " " * 98, color)
                    self._pad.addstr(2+((i-offset)*3)+1, 1, " " * 98, color)

                self._pad.addstr(2+((i-offset)*3), 1, "{}".format(
                    isoformatseconds(datetime.datetime.utcfromtimestamp(tx["timereceived"]))
                ), color)
                self._pad.addstr(2+((i-offset)*3), 30, "block: {: 7d}".format(tx["blockindex"]), color)
                self._pad.addstr(2+((i-offset)*3), 81, "{: 15.8f} BTC".format(
                    tx["amount"],
                ), color)
                self._pad.addstr(2+((i-offset)*3)+1, 1, "{}".format(tx["address"]), color)
                self._pad.addstr(2+((i-offset)*3)+1, 36, "{}".format(tx["txid"]), color)

    async def _draw(self):
        self._clear_init_pad()

        if self._wallet:
            await self._draw_wallet(self._wallet)

        self._draw_pad_to_screen()

    async def on_sinceblock(self, key, obj):
        # TODO: if no changes don't reset cursor or do anything?
        try:
            wallet = obj["result"]
        except KeyError:
            return

        if wallet is None:
            # probably a disabled wallet.
            return

        if self._wallet is not None:
            if wallet["lastblock"] == self._wallet["lastblock"]:
                # No change.
                return

        def sort_wallet_tx(tx):
            return (tx["timereceived"], tx["amount"])

        # Sort it.
        wallet["transactions"] = sorted(wallet["transactions"], key=sort_wallet_tx, reverse=True)

        self._wallet = wallet

        # TODO: scan the old and new wallets, select the same tx, update offset.

        if self._selected_tx is None:
            self._selected_tx = (0, None)

        if self._tx_offset is None:
            self._tx_offset = (0, None)

        await self._draw_if_visible()

    async def _select_previous_transaction(self):
        """
        if self._hash is None:
            return # Can't do anything

        if self._selected_tx == None or self._selected_tx[1] != self._hash:
            return # Can't do anything

        if self._tx_offset == None or self._tx_offset[1] != self._hash:
            return # Can't do anything
        """

        if not self._wallet:
            return

        if self._selected_tx[0] == 0:
            return # At the beginning already.

        if self._selected_tx[0] == self._tx_offset[0]:
            self._tx_offset = (self._tx_offset[0] - 1, self._tx_offset[1])

        self._selected_tx = (self._selected_tx[0] - 1, self._selected_tx[1])

        await self._draw_if_visible()

    async def _select_next_transaction(self):
        """
        if self._hash is None:
            return # Can't do anything

        if self._selected_tx == None or self._selected_tx[1] != self._hash:
            return # Can't do anything

        if self._tx_offset == None or self._tx_offset[1] != self._hash:
            return # Can't do anything
        """

        if not self._wallet:
            return

        if self._selected_tx[0] == len(self._wallet["transactions"]) - 1:
            return # At the end already

        if self._selected_tx[0] == self._tx_offset[0] + 5:
            self._tx_offset = (self._tx_offset[0] + 1, self._tx_offset[1])

        self._selected_tx = (self._selected_tx[0] + 1, self._selected_tx[1])

        await self._draw_if_visible()

    async def _enter_transaction_view(self):
        """
        if self._hash is None:
            return # Can't do anything

        if self._selected_tx == None or self._selected_tx[1] != self._hash:
            return # Can't do anything

        if self._tx_offset == None or self._tx_offset[1] != self._hash:
            return # This shouldn't matter, but skip anyway
        """

        if self._selected_tx == None:
            return # Can't do anything

        txid = self._wallet["transactions"][self._selected_tx[0]]["txid"]

        await self._txidsetter(txid)
        await self._modesetter("transaction")

    async def handle_keypress(self, key):
        assert self._visible

        if key == "KEY_UP":
            await self._select_previous_transaction()
            return None

        if key == "KEY_DOWN":
            await self._select_next_transaction()
            return None

        if key == "KEY_RETURN" or key == "\n":
            await self._enter_transaction_view()
            return None

        return key
