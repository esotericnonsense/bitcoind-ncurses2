# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import argparse
import os
import asyncio
import datetime

import rpc
import interface
import header
import footer
import monitor
import peers

from macros import MODES, DEFAULT_MODE


async def handle_hotkeys(window, callback):

    async def handle_key(key):
        if key == "KEY_LEFT":
            await callback(None, seek=-1)
            return

        if key == "KEY_RIGHT":
            await callback(None, seek=1)
            return

        if len(key) > 1:
            return

        lower = key.lower()

        for mode in MODES:
            if mode[0] == lower:
                await callback(mode)

    first = True
    while True:
        # This is basically spinning which is really annoying.
        # TODO: find a way of having async blocking getch/getkey.
        try:
            key = window.getkey()
        except Exception:
            # This is bonkers and I don't understand it.
            if first:
                await callback(DEFAULT_MODE)
                first = False

            await asyncio.sleep(0.05)
            continue

        await handle_key(key)


async def poll_client(client, method, callback, sleeptime):
    # Allow the rest of the program to start.
    await asyncio.sleep(0.1)

    while True:
        j = await client.request(method)
        await callback(method, j)
        await asyncio.sleep(sleeptime)


async def tick(callback, sleeptime):
    # Allow the rest of the program to start.
    await asyncio.sleep(0.1)

    while True:
        dt = datetime.datetime.utcnow()
        await callback(dt)
        await asyncio.sleep(sleeptime)


def initialize():
    # parse commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--datadir",
                        help="path to bitcoin datadir [~/.bitcoin/]",
                        default=os.path.expanduser("~/.bitcoin/"))
    args = parser.parse_args()

    url = rpc.get_url_from_datadir(args.datadir)
    auth = rpc.get_auth_from_datadir(args.datadir)
    client = rpc.BitcoinRPCClient(url, auth)

    return client


def check_disablewallet(client):
    """ Check if the wallet is enabled. """

    # Ugly, a synchronous RPC request mechanism would be nice here.
    x = asyncio.gather(client.request("getwalletinfo"))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(x)

    try:
        x.result()[0]["result"]["walletname"]
    except (KeyError, TypeError):
        return True

    return False


def create_tasks(client, window):
    headerview = header.HeaderView()
    footerview = footer.FooterView()

    monitorview = monitor.MonitorView(client)
    peerview = peers.PeersView()
    footerview.add_callback(monitorview.on_mode_change)
    footerview.add_callback(peerview.on_mode_change)

    async def on_peerinfo(key, obj):
        await headerview.on_peerinfo(key, obj)
        await peerview.on_peerinfo(key, obj)

    async def on_tick(dt):
        await footerview.on_tick(dt)
        await monitorview.on_tick(dt)

    tasks = [
        poll_client(client, "getbestblockhash",
                    monitorview.on_bestblockhash, 1.0),
        poll_client(client, "getblockchaininfo",
                    headerview.on_blockchaininfo, 5.0),
        poll_client(client, "getnetworkinfo",
                    headerview.on_networkinfo, 5.0),
        poll_client(client, "getnettotals",
                    headerview.on_nettotals, 5.0),
        poll_client(client, "getpeerinfo",
                    on_peerinfo, 5.0),
        tick(on_tick, 1.0),
        handle_hotkeys(window, footerview.on_mode_change)
    ]

    if not check_disablewallet(client):
        tasks.append(
            poll_client(client, "getwalletinfo", headerview.on_walletinfo, 1.0)
        )

    return tasks


def mainfn():
    client = initialize()

    try:
        window = interface.init_curses()
        tasks = create_tasks(client, window)

        loop = asyncio.get_event_loop()
        t = asyncio.gather(*tasks)
        loop.run_until_complete(t)

    finally:
        try:
            loop.close()
        except BaseException:
            pass
        interface.end_curses()


if __name__ == "__main__":
    mainfn()
