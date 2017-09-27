# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import curses
import platform

from macros import VERSION_STRING, MIN_WINDOW_SIZE


class HeaderView(object):
    def __init__(self):
        # one larger than we will ever draw otherwise we can't populate
        # the bottom-right
        self._pad = curses.newpad(2, 101)

        self._platform = "{} {} {}".format(
            platform.system(),
            platform.release(),
            platform.machine(),
        )

        self._subversion = None
        self._chain = None
        self._connectioncount = None
        self._nettotals = None
        self._balance = None

        self._window_size = MIN_WINDOW_SIZE

    def draw(self):
        # TODO: figure out window width etc.

        self._pad.clear()

        CGREEN = curses.color_pair(1)
        CCYAN = curses.color_pair(2)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD

        colors = {
            "main": CGREEN + CBOLD,
            "test": CCYAN + CBOLD,
            "regtest": CRED + CBOLD,
        }
        currencies = {
            "main": "BTC",
            "test": "tBC",
            "regtest": "rBC",
        }
        version_color = colors.get(self._chain, CBOLD)
        currency = currencies.get(self._chain, "???")
        chn = self._chain if self._chain is not None else "???"

        self._pad.addstr(0, 1, "{} ({})".format(
            VERSION_STRING[:30],
            chn
        ), version_color)

        if self._connectioncount is not None:
            if self._connectioncount > 8:
                peercolor = CGREEN + CBOLD
            elif self._connectioncount > 0:
                peercolor = CBOLD
            else:
                peercolor = CRED + CBOLD

            self._pad.addstr(0, 37, "{: 4d} {}".format(
                self._connectioncount,
                "peers" if self._connectioncount != 1 else "peer"
            ), peercolor)

        if self._subversion:
            self._pad.addstr(1, 1, "{} / {}".format(
                self._platform[:27],
                self._subversion.strip("/").strip(":")[:18]
            ), version_color)

        if self._nettotals is not None:
            self._pad.addstr(0, 51, "Up:   {: 9.2f} MB".format(
                self._nettotals[1] / 1048576,
            ), CBOLD + CCYAN)
            self._pad.addstr(1, 51, "Down: {: 9.2f} MB".format(
                self._nettotals[0] / 1048576,
            ), CBOLD + CGREEN)

        if self._balance is not None:
            self._pad.addstr(0, 82, "{: 14.8f} {}".format(
                self._balance[0],
                currency
            ), CBOLD)

            # We only show unconfirmed if we have both unc/imm. So it goes.
            if self._balance[1] != 0:
                self._pad.addstr(1, 69, "unconfirmed: {: 14.8f} {}".format(
                    self._balance[1],
                    currency,
                ), CBOLD + CYELLOW)
            elif self._balance[2] != 0:
                self._pad.addstr(1, 72, "immature: {: 14.8f} {}".format(
                    self._balance[2],
                    currency,
                ), CBOLD + CRED)
        else:
            self._pad.addstr(0, 85, "wallet disabled", CBOLD + CRED)

        self._draw_pad_to_screen()

    def _draw_pad_to_screen(self):
        maxy, maxx = self._window_size
        if maxy < 3 or maxx < 3:
            # can't do it
            return

        self._pad.refresh(0, 0, 1, 0, min(maxy, 2), min(maxx-1, 100))

    async def on_networkinfo(self, key, obj):
        try:
            self._subversion = obj["result"]["subversion"]
        except KeyError:
            pass

        self.draw()

    async def on_blockchaininfo(self, key, obj):
        try:
            self._chain = obj["result"]["chain"]
        except KeyError:
            pass

        self.draw()

    async def on_peerinfo(self, key, obj):
        try:
            self._connectioncount = len(obj["result"])
        except KeyError:
            pass

        self.draw()

    async def on_nettotals(self, key, obj):
        try:
            tbr = obj["result"]["totalbytesrecv"]
            tbs = obj["result"]["totalbytessent"]
            self._nettotals = (tbr, tbs)
        except KeyError:
            pass

        self.draw()

    async def on_walletinfo(self, key, obj):
        try:
            bal = obj["result"]["balance"]
            ubal = obj["result"]["unconfirmed_balance"]
            ibal = obj["result"]["immature_balance"]
            self._balance = (bal, ubal, ibal)
        except KeyError:
            pass

        self.draw()

    async def on_window_resize(self, y, x):
        # At the moment we ignore the x size and limit to 100.
        self._window_size = (y, x)
        self.draw()
