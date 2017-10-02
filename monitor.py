# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import datetime
import math
import curses
import asyncio
from decimal import Decimal

import view
from rpc import RPCError


class MonitorView(view.View):
    _mode_name = "monitor"

    def __init__(self, client):
        self._client = client

        self._lock = asyncio.Lock()
        self._bestblockhash = None
        self._bestblockheader = None  # raw json blockheader
        self._bestblock = None  # raw json block
        self._bestcoinbase = (None, None)  # (blockhash, raw json tx)
        self._mempoolinfo = None  # raw mempoolinfo
        self._estimatesmartfee = {} # blocks -> feerate/kB
        self._dt = None
        self._uptime = None # raw uptime from bitcoind (seconds)

        super().__init__()

    async def _draw(self):
        self._clear_init_pad()

        if self._mempoolinfo:
            self._pad.addstr(9, 1, "Mempool transactions: {: 6d} ({: 5.2f} MiB)".format(
                self._mempoolinfo["size"],
                self._mempoolinfo["bytes"] / 1048576,
            ))

        if self._estimatesmartfee:
            estimates = " ".join(
                    "({: 2d}: {: 8.0f} sat/kB)".format(b, fr*10**8)
                for b, fr in sorted(self._estimatesmartfee.items())
            )
            self._pad.addstr(11, 1, "estimatesmartfee: {}".format(estimates))

        if self._uptime:
            self._pad.addstr(13, 1, "uptime: {}".format(datetime.timedelta(seconds=self._uptime)))

        bbh = self._bestblockhash
        if not bbh:
            self._draw_pad_to_screen()
            return

        self._pad.addstr(0, 36, bbh)

        bbhd = self._bestblockheader
        if not bbhd or bbhd["hash"] != bbh:
            self._draw_pad_to_screen()
            return

        self._pad.addstr(0, 1, "Height: {: 8d}".format(bbhd["height"]))

        bb = self._bestblock
        if not bb or bb["hash"] != bbh:
            self._draw_pad_to_screen()
            return

        bb = self._bestblock
        self._pad.addstr(1, 1, "Size: {: 8d} bytes               Weight: {: 8d} WU".format(
            bb["size"],
            bb["weight"]
        ))

        self._pad.addstr(1, 64, "Block timestamp: {}".format(
            datetime.datetime.utcfromtimestamp(bb["time"]),
        ))

        self._pad.addstr(2, 1, "Transactions: {} ({} bytes/tx, {} WU/tx)".format(
            len(bb["tx"]),
            bb["size"] // len(bb["tx"]),
            bb["weight"] // len(bb["tx"]),
        ))

        self._pad.addstr(6, 1, "Diff: {:,}".format(
            int(bb["difficulty"]),
        ))
        self._pad.addstr(7, 1, "Chain work: 2**{:.6f}".format(
            math.log(int(bb["chainwork"], 16), 2),
        ))

        if self._dt:
            stampdelta = int(
                (self._dt - datetime.datetime.utcfromtimestamp(bb["time"]))
                .total_seconds())

            if stampdelta > 3600*3:  # probably syncing
                stampdelta_string = "             (syncing)"

            elif stampdelta > 0:
                m, s = divmod(stampdelta, 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                stampdelta_string = "({:d}d {:02d}:{:02d}:{:02d} by stamp)".format(d,h,m,s)

            else:
                stampdelta_string = "     (stamp in future)"

            self._pad.addstr(2, 64, "Age:          {}".format(
                stampdelta_string))

        # TODO: check the coinbase is associated with this block.
        (h, bcb) = self._bestcoinbase
        if not bcb or h != bbh:
            self._draw_pad_to_screen()
            return

        reward = sum(vout["value"] for vout in bcb["vout"])

        # TODO: if chain is regtest, this is different
        halvings = bb["height"] // 210000
        block_subsidy = Decimal(50 * (0.5 ** halvings))

        total_fees = Decimal(reward) - block_subsidy

        self._pad.addstr(4, 1, "Block reward: {:.6f} BTC".format(
            reward))

        if len(bb["tx"]) > 1:
            if reward > 0:
                fee_pct = total_fees * 100 / Decimal(reward)
            else:
                fee_pct = 0
            mbtc_per_tx = (total_fees / (len(bb["tx"]) - 1)) * 1000

            # 80 bytes for the block header.
            total_tx_size = bb["size"] - 80 - bcb["size"]
            if total_tx_size > 0:
                sat_per_kb = ((total_fees * 1024) / total_tx_size) * 100000000
            else:
                sat_per_kb = 0
            self._pad.addstr(4, 34, "Fees: {: 8.6f} BTC ({: 6.2f}%, avg {: 6.2f} mBTC/tx, ~{: 7.0f} sat/kB)".format(total_fees, fee_pct, mbtc_per_tx, sat_per_kb))

        self._draw_pad_to_screen()

    async def _draw_if_visible(self):
        """ Override the view.View method because we need to lock. """
        with await self._lock:
            if self._visible:
                await self._draw()

    async def _request_bestblockhash_info(self, bestblockhash):
        try:
            j = await self._client.request("getblockheader", [bestblockhash])
            self._bestblockheader = j["result"]
        except RPCError:
            return

        try:
            j = await self._client.request("getblock", [bestblockhash])
            h = j["result"]["hash"]
            self._bestblock = j["result"]
        except (RPCError, KeyError):
            return

        try:
            j = await self._client.request("getrawtransaction", [j["result"]["tx"][0], 1])
            self._bestcoinbase = (h, j["result"])
        except RPCError:
            return

    async def on_bestblockhash(self, key, obj):
        try:
            bestblockhash = obj["result"]
        except KeyError:
            return

        draw = False
        with await self._lock:
            if bestblockhash != self._bestblockhash:
                draw = True
                self._bestblockhash = bestblockhash
                await self._request_bestblockhash_info(bestblockhash)

        if draw:
            await self._draw_if_visible()

    async def on_mempoolinfo(self, key, obj):
        try:
            self._mempoolinfo = obj["result"]
        except KeyError:
            return

        await self._draw_if_visible()

    async def on_estimatesmartfee(self, key, obj):
        try:
            estimatesmartfee = obj["result"]
        except KeyError:
            return

        try:
            b, fr = estimatesmartfee["blocks"], estimatesmartfee["feerate"]
            self._estimatesmartfee[b] = fr
        except KeyError:
            self._estimatesmartfee = None

        await self._draw_if_visible()

    async def on_tick(self, dt):
        with await self._lock:
            self._dt = dt

        await self._draw_if_visible()

    async def on_uptime(self, key, obj):
        try:
            self._uptime = obj["result"]
        except KeyError:
            return

        await self._draw_if_visible()
