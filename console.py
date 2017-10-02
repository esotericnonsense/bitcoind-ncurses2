# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import curses
import curses.textpad
import asyncio
import decimal

try:
    import ujson as json
except ImportError:
    import json

import view
from rpc import RPCError


class ConsoleView(view.View):
    _mode_name = "console"

    def __init__(self, client):
        self._client = client

        self._textbox_active = False
        # TODO: implement history properly
        self._command_history = [""]
        self._response_history = []
        self._response_history_strings = []
        self._response_history_offset = 0

        super().__init__()

    async def _draw(self):
        self._clear_init_pad()

        CGREEN = curses.color_pair(1)
        CRED = curses.color_pair(3)
        CYELLOW = curses.color_pair(5)
        CBOLD = curses.A_BOLD
        CREVERSE = curses.A_REVERSE

        self._pad.addstr(0, 63, "[UP/DOWN: browse, TAB: enter command]", CYELLOW)
        offset = self._response_history_offset
        if offset > 0:
            self._pad.addstr(0, 36, "... ^ ...", CBOLD)
        if offset < len(self._response_history_strings) - 17:
            self._pad.addstr(17, 36, "... v ...", CBOLD)

        for i, (t, string) in enumerate(self._response_history_strings):
            if i < offset:
                continue
            if i > offset+15: # TODO
                break

            color = CBOLD + CGREEN if t == 0 else CBOLD
            self._pad.addstr(1+i-offset, 1, string, color)

        cmd = self._command_history[-1]
        cmd2 = None
        if len(cmd) > 97:
            cmd2, cmd = cmd[97:], cmd[:97]

        self._pad.addstr(18, 1, "> {}".format(cmd),
            CRED + CBOLD + CREVERSE if self._textbox_active else 0)
        if cmd2 is not None:
            self._pad.addstr(19, 3, cmd2,
                CRED + CBOLD + CREVERSE if self._textbox_active else 0)

        self._draw_pad_to_screen()

    @staticmethod
    def _convert_reqresp_to_strings(request, response):
        srequest = [
            (0, request[i:i+95])
            for i in range(0, len(request), 95)
        ]
        srequest[0] = (0, ">>> " + srequest[0][1])

        jresponse = json.dumps(response, indent=4, sort_keys=True).split("\n")
        # TODO: if error, set 2 not 1
        sresponse = [
            (1, l[i:i+99])
            for l in jresponse
            for i in range(0, len(l), 99)
        ]

        return srequest + sresponse + [(-1, "")]

    async def _submit_command(self):
        # TODO: parse, allow nested, use brackets etc
        request = self._command_history[-1]
        if len(request) == 0:
            return

        parts = request.split(" ")
        for i in range(len(parts)):
            # TODO: parse better.
            if parts[i].isdigit():
                parts[i] = int(parts[i])
            elif parts[i] == "false" or parts[i] == "False":
                parts[i] = False
            elif parts[i] == "true" or parts[i] == "True":
                parts[i] = True
            else:
                try:
                    parts[i] = decimal.Decimal(parts[i])
                except: 
                    pass

        cmd = parts[0]
        if len(parts) > 1:
            params = parts[1:]
        else:
            params = None

        try:
            response = await self._client.request(cmd, params=params)
        except RPCError as e:
            response = str(e)

        self._response_history.append(
            (request, response),
        )
        self._response_history_strings.extend(
            self._convert_reqresp_to_strings(request, response),
        )

        self._command_history.append("") # add a new, empty command
        self._response_history_offset = len(self._response_history_strings) - 17
        self._textbox_active = not self._textbox_active

        await self._draw_if_visible()

    async def _scroll_back_response_history(self):
        if self._response_history_offset == 0:
            return # At the beginning already.

        self._response_history_offset -= 1

        await self._draw_if_visible()

    async def _scroll_forward_response_history(self):
        if self._response_history_offset > len(self._response_history_strings) - 18:
            return # At the end already.

        self._response_history_offset += 1

        await self._draw_if_visible()

    async def handle_keypress(self, key):
        if key == "\t" or key == "KEY_TAB":
            self._textbox_active = not self._textbox_active
            key = None
        elif self._textbox_active:
            if (len(key) == 1 and ord(key) == 127) or key == "KEY_BACKSPACE":
                self._command_history[-1] = self._command_history[-1][:-1]

                key = None
            elif key == "KEY_RETURN" or key == "\n":
                # We use ensure_future so as not to block the keypad loop on
                #   an RPC call
                # asyncio.ensure_future(self._submit_command())
                await self._submit_command()
                return None
            elif len(key) == 1:
                # TODO: check if it's printable etc
                if len(self._command_history[-1]) < 190:
                    self._command_history[-1] += key

                key = None
        else:
            if key == "KEY_UP":
                await self._scroll_back_response_history()
                key = None
            elif key == "KEY_DOWN":
                await self._scroll_forward_response_history()
                key = None

        await self._draw_if_visible()

        return key

    async def on_mode_change(self, newmode):
        """ Overrides view.View to set the textbox inactive. """
        if newmode != self._mode_name:
            self._textbox_active = False
            self._visible = False
            return

        self._visible = True
        await self._draw_if_visible()
