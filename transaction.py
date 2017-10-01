# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import datetime
import curses
import asyncio

import view
from macros import TX_VERBOSE_MODE


class TransactionStore(object):
    def __init__(self, client):
        self._client = client

        self._lock = asyncio.Lock()

        self._transactions = {}  # txid -> raw transaction

    async def get_transaction(self, txid):
        with await self._lock:
            try:
                return self._transactions[txid]
            except KeyError:
                # TODO: handle error if the transaction doesn't exist at all.
                j = await self._client.request("getrawtransaction", [txid, True])
                self._transactions[txid] = j["result"]
                return j["result"]


class TransactionView(view.View):
    _mode_name = "transaction"

    def __init__(self, transactionstore):
        self._transactionstore = transactionstore

        self._txid = None  # currently browsed txid.
        self._selected_input = None # (index, txid)
        self._input_offset = None # (offset, txid)
        self._selected_output = None # (index, txid)
        self._output_offset = None # (offset, txid)

        super().__init__()

    async def _set_txid(self, txid, vout=None):
        # TODO: lock?
        self._txid = txid
        self._selected_input = (0, txid)
        self._input_offset = (0, txid)
        if vout is not None: # A specific input was selected, go there.
            self._selected_output = (vout, txid)
            self._output_offset = (vout, txid)
        else:
            self._selected_output = (0, txid)
            self._output_offset = (0, txid)

    async def set_txid(self, txid):
        # Externally setting vout is not permitted/necessary.
        await self._set_txid(txid)

    async def _draw_transaction(self, transaction):
        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD

        self._pad.addstr(0, 1, "time {}".format(
            datetime.datetime.utcfromtimestamp(transaction["time"]).isoformat(timespec="seconds")
        ), CBOLD)
        self._pad.addstr(1, 1, "size {}b".format(transaction["size"]), CBOLD)
        self._pad.addstr(1, 15, "vsize {}b".format(transaction["vsize"]), CBOLD)
        self._pad.addstr(2, 1, "locktime {}".format(transaction["locktime"]), CBOLD)
        self._pad.addstr(2, 23, "v{}".format(transaction["version"]), CBOLD)

        self._pad.addstr(0, 31, "txid {}".format(transaction["txid"]), CBOLD)
        self._pad.addstr(1, 31, "hash {}".format(transaction["hash"]), CBOLD)
        if "blockhash" in transaction:
            self._pad.addstr(2, 30, "block {}".format(transaction["blockhash"]), CBOLD)
        else:
            self._pad.addstr(2, 58, "unconfirmed transaction!", CBOLD + CRED)

        # height and weight would be nice.
        # neither are directly accessible.

    async def _draw_inputs(self, transaction, inouts):
        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        self._pad.addstr(4, 1, "Inputs: {}".format(len(transaction["vin"])), CRED + CBOLD)
        self._pad.addstr(4, 68, "[UP/DOWN: browse, ENTER: select]", CYELLOW)

        if self._selected_input is None or self._input_offset is None:
            # Shouldn't happen
            raise Exception

        if self._selected_input[1] != transaction["txid"] or self._input_offset[1] != transaction["txid"]:
            # Shouldn't happen
            raise Exception

        offset = self._input_offset[0]
        if offset > 0:
            self._pad.addstr(5, 36, "... ^ ...", CRED + CBOLD)
        if offset < len(transaction["vin"]) - 5:
            self._pad.addstr(11, 36, "... v ...", CRED + CBOLD)
        for i, inp in enumerate(transaction["vin"]):
            if i < offset: # this is lazy
                continue
            if i > offset+4: # this is lazy
                break

            # Sequence numbers, perhaps?
            if "coinbase" in inp:
                inputstr = inp["coinbase"][:76]
            elif inouts is not None: # TX_VERBOSE_MODE
                # Find the vout
                inout = inouts[i]
                inputstr = "{}".format(str(inout)[:40])
                spk = inout["scriptPubKey"]
                if "addresses" in spk:
                    if len(spk["addresses"]) > 1:
                        inoutstring = "<{} addresses>".format(len(spk["addresses"]))
                    elif len(spk["addresses"]) == 1:
                        inoutstring = spk["addresses"][0].rjust(34)
                    else:
                        raise Exception("addresses present in scriptPubKey, but 0 addresses")
                elif "asm" in spk:
                    inoutstring = spk["asm"][:34]
                else:
                    inoutstring = "???"

                inputstr = "{:05d} {} {: 15.8f} BTC".format(i, inoutstring, inout["value"])
            else:
                inputstr = "{:05d} {}:{:05d}".format(i, inp["txid"], inp["vout"])

            if i == self._selected_input[0] and self._txid == self._selected_input[1]:
                inputcolor = CRED + CBOLD + CREVERSE
            else:
                inputcolor = CRED

            self._pad.addstr(6+i-offset, 24, inputstr, inputcolor)

    async def _draw_outputs(self, transaction):
        # TODO: can we reuse code from _draw_inputs?
        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        self._pad.addstr(12, 1, "[PGUP/PGDN: browse]", CYELLOW)
        out_total = sum(out["value"] for out in transaction["vout"])
        self._pad.addstr(12, 64, "Outputs: {: 5d} ({: 15.8f} BTC)".format(len(transaction["vout"]), out_total), CGREEN + CBOLD)

        if self._selected_output is None or self._output_offset is None:
            # Shouldn't happen
            raise Exception

        if self._selected_output[1] != transaction["txid"] or self._output_offset[1] != transaction["txid"]:
            # Shouldn't happen
            raise Exception

        offset = self._output_offset[0]
        if offset > 0:
            self._pad.addstr(13, 36, "... ^ ...", CGREEN + CBOLD)
        if offset < len(transaction["vout"]) - 5:
            self._pad.addstr(19, 36, "... v ...", CGREEN + CBOLD)
        for i, out in enumerate(transaction["vout"]):
            if i < offset: # this is lazy
                continue
            if i > offset+4: # this is lazy
                break

            # A 1 million BTC output would be rather surprising. Pad to six.
            spk = out["scriptPubKey"]
            if "addresses" in spk:
                if len(spk["addresses"]) > 1:
                    outstring = "<{} addresses>".format(len(spk["addresses"]))
                elif len(spk["addresses"]) == 1:
                    outstring = spk["addresses"][0].rjust(34)
                else:
                    raise Exception("addresses present in scriptPubKey, but 0 addresses")
            elif "asm" in spk:
                outstring = spk["asm"][:80]
            else:
                outstring = "???"

            if i == self._selected_output[0] and self._txid == self._selected_output[1]:
                outputcolor = CGREEN + CBOLD + CREVERSE
            else:
                outputcolor = CGREEN

            self._pad.addstr(14+i-offset, 1, "{:05d} {} {: 15.8f} BTC".format(i, outstring, out["value"]), outputcolor)

    async def _draw_no_transaction(self):
        CRED = curses.color_pair(3)
        CBOLD = curses.A_BOLD
        self._pad.addstr(0, 1, "no transaction loaded", CRED + CBOLD)
        self._pad.addstr(1, 1, "enter block view and select a transaction", CRED)
        self._pad.addstr(2, 1, "note that most transactions will be unavailable if -txindex is not enabled on your node", CRED)

    async def _draw(self):
        self._clear_init_pad()

        transaction = None
        inouts = None
        if self._txid:
            transaction = await self._transactionstore.get_transaction(self._txid)
            if TX_VERBOSE_MODE:
                inouts = []
                for vin in transaction["vin"]:
                    if not "txid" in vin:
                        # It's a coinbase
                        inouts = None
                        break
                    prevtx = await self._transactionstore.get_transaction(vin["txid"])
                    inouts.append(prevtx["vout"][vin["vout"]])

        if transaction:
            await self._draw_transaction(transaction)
            if "vin" in transaction:
                await self._draw_inputs(transaction, inouts)
            if "vout" in transaction:
                await self._draw_outputs(transaction)
        else:
            await self._draw_no_transaction()

        self._draw_pad_to_screen()

    async def _select_previous_input(self):
        if self._txid is None:
            return # Can't do anything

        if self._selected_input == None or self._selected_input[1] != self._txid:
            return # Can't do anything

        if self._input_offset == None or self._input_offset[1] != self._txid:
            return # Can't do anything

        if self._selected_input[0] == 0:
            return # At the beginning already.

        if self._selected_input[0] == self._input_offset[0]:
            self._input_offset = (self._input_offset[0] - 1, self._input_offset[1])

        self._selected_input = (self._selected_input[0] - 1, self._selected_input[1])

        await self._draw_if_visible()

    async def _select_next_input(self):
        if self._txid is None:
            return # Can't do anything

        if self._selected_input == None or self._selected_input[1] != self._txid:
            return # Can't do anything

        if self._input_offset == None or self._input_offset[1] != self._txid:
            return # Can't do anything

        try:
            transaction = await self._transactionstore.get_transaction(self._txid)
        except KeyError:
            return # Can't do anything

        if self._selected_input[0] == len(transaction["vin"]) - 1:
            return # At the end already

        if self._selected_input[0] == self._input_offset[0] + 4:
            self._input_offset = (self._input_offset[0] + 1, self._input_offset[1])

        self._selected_input = (self._selected_input[0] + 1, self._selected_input[1])

        await self._draw_if_visible()

    async def _select_input_as_transaction(self):
        if self._txid is None:
            return # Can't do anything

        if self._selected_input == None or self._selected_input[1] != self._txid:
            return # Can't do anything

        if self._input_offset == None or self._input_offset[1] != self._txid:
            return # This shouldn't matter, but skip anyway

        try:
            transaction = await self._transactionstore.get_transaction(self._txid)
        except KeyError:
            return # Can't do anything

        inp = transaction["vin"][self._selected_input[0]]
        # Sequence numbers, perhaps?
        if "coinbase" in inp:
            return # Can't do anything
        else:
            await self._set_txid(inp["txid"], vout=inp["vout"])

        await self._draw_if_visible()

    async def _select_previous_output(self):
        if self._txid is None:
            return # Can't do anything

        if self._selected_output == None or self._selected_output[1] != self._txid:
            return # Can't do anything

        if self._output_offset == None or self._output_offset[1] != self._txid:
            return # Can't do anything

        if self._selected_output[0] == 0:
            return # At the beginning already.

        if self._selected_output[0] == self._output_offset[0]:
            self._output_offset = (self._output_offset[0] - 1, self._output_offset[1])

        self._selected_output = (self._selected_output[0] - 1, self._selected_output[1])

        await self._draw_if_visible()

    async def _select_next_output(self):
        if self._txid is None:
            return # Can't do anything

        if self._selected_output == None or self._selected_output[1] != self._txid:
            return # Can't do anything

        if self._output_offset == None or self._output_offset[1] != self._txid:
            return # Can't do anything

        try:
            transaction = await self._transactionstore.get_transaction(self._txid)
        except KeyError:
            return # Can't do anything

        if self._selected_output[0] == len(transaction["vout"]) - 1:
            return # At the end already

        if self._selected_output[0] == self._output_offset[0] + 4:
            self._output_offset = (self._output_offset[0] + 1, self._output_offset[1])

        self._selected_output = (self._selected_output[0] + 1, self._selected_output[1])

        await self._draw_if_visible()

    async def handle_keypress(self, key):
        assert self._visible

        if key == "KEY_UP":
            await self._select_previous_input()
            return None

        if key == "KEY_DOWN":
            await self._select_next_input()
            return None

        if key.lower() == "j" or key == "KEY_PPAGE":
            await self._select_previous_output()
            return None

        if key.lower() == "k" or key == "KEY_NPAGE":
            await self._select_next_output()
            return None

        if key == "KEY_RETURN" or key == "\n":
            await self._select_input_as_transaction()
            return None

        return key
