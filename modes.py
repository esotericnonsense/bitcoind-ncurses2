# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

from macros import MODES


class ModeHandler(object):
    def __init__(self, base_callbacks):
        self._mode = None

        self._callbacks = {}  # mode -> callback, one per mode.
        self._base_callbacks = base_callbacks

        self._keypress_handlers = {}  # mode -> keypress handler.

    def add_callback(self, key, callback):
        self._callbacks[key] = callback

    def add_keypress_handler(self, key, handler):
        self._keypress_handlers[key] = handler

    async def _call_callbacks(self, oldmode, newmode):
        # Tell the old mode that it's no longer active
        try:
            cb1 = self._callbacks[oldmode]
        except KeyError:
            cb1 = None

        if cb1 is not None:
            await cb1(newmode)

        # Tell the new mode that it's now active
        try:
            cb2 = self._callbacks[newmode]
        except KeyError:
            cb2 = None

        if cb2 is not None:
            await cb2(newmode)

        # Base callbacks (FooterView, HeaderView)
        for bcb in self._base_callbacks:
            await bcb(newmode)

    async def set_mode(self, newmode):
        if self._mode == newmode:
            return

        await self._call_callbacks(self._mode, newmode)
        self._mode = newmode

    async def _seek_mode(self, seek):
        if self._mode is None:
            # Can't seek if no mode
            return

        idx = MODES.index(self._mode)
        idx = (idx + seek) % len(MODES)
        newmode = MODES[idx]

        await self.set_mode(newmode)

    async def handle_keypress(self, key):
        # See if the current mode can handle it.
        if self._mode is None:
            return key

        handler = None
        try:
            handler = self._keypress_handlers[self._mode]
        except KeyError:
            pass

        if handler:
            key = await handler(key)

        if key is None:
            return key

        # See if it's related to switching modes.
        if key == "KEY_LEFT":
            await self._seek_mode(-1)
            return None

        if key == "KEY_RIGHT":
            await self._seek_mode(1)
            return None

        if len(key) == 1:
            for mode in MODES:
                if mode[0] == key.lower():
                    await self.set_mode(mode)
                    return None

        return key  # Either none by this point, or still there.
