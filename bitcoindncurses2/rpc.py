# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

import aiohttp
import asyncio
import async_timeout
import base64
import os

try:
    import ujson as json
except ImportError:
    import json

from . import config


def craft_url(proto, ip, port):
    return "{}://{}:{}".format(proto, ip, port)


def get_url_from_datadir(datadir):
    configfile = os.path.join(datadir, "bitcoin.conf")

    try:
        cfg = config.parse_file(configfile)
    except IOError:
        return craft_url("http", "localhost", 8332)

    proto = cfg["protocol"] if "protocol" in cfg else "http"
    ip = cfg["rpcconnect"] if "rpcconnect" in cfg else "localhost"
    try:
        port = cfg["rpcport"]
    except KeyError:
        # If both regtest and testnet are set, bitcoind will not run.
        if "regtest" in cfg and cfg["regtest"] == "1":
            port = 18332
        elif "testnet" in cfg and cfg["testnet"] == "1":
            port = 18332
        else:
            port = 8332

    return craft_url(proto, ip, port)


def get_auth_from_datadir(datadir):
    def craft_auth_from_credentials(user, password):
        details = ":".join([user, password])
        return base64.b64encode(bytes(details, "utf-8")).decode("utf-8")

    def get_auth_from_cookiefile(cookiefile):
        # Raises IOError if file does not exist
        with open(cookiefile, "r") as f:
            return base64.b64encode(bytes(f.readline(), "utf-8")).decode("utf-8")

    cookiefile = os.path.join(datadir, ".cookie")

    try:
        return get_auth_from_cookiefile(cookiefile)
    except FileNotFoundError:
        print("cookiefile not found, falling back to password authentication")
        # Fall back to credential-based authentication
        configfile = os.path.join(datadir, "bitcoin.conf")

        try:
            cfg = config.parse_file(configfile)
        except IOError:
            print("configuration file not found; aborting.")
            raise

        try:
            rpcuser = cfg["rpcuser"]
            rpcpassword = cfg["rpcpassword"]
        except KeyError:
            if not ("rpcuser" in cfg):
                print("rpcuser not in configuration file.")
            if not ("rpcpassword" in cfg):
                print("rpcpassword not in configuration file.")
            raise

        return craft_auth_from_credentials(rpcuser, rpcpassword)

class RPCError(BaseException):
    """ Parent class for the RPC errors. """
    pass

class RPCContentError(RPCError):
    # TODO: include the error code, etc.
    pass


class RPCTimeoutError(RPCError):
    # TODO: include the timeout value?
    pass


class RPCConnectionError(RPCError):
    pass


class BitcoinRPCClient(object):
    def __init__(self, url, auth):
        self._url = url
        self._headers = {
            "Authorization": "Basic {}".format(auth),
            "Content-Type": "text/plain",
        }

    @staticmethod
    async def _craft_request(req, params, ident):
        d = {
            # "jsonrpc": "2.0",  # Currently ignored by Bitcoin Core.
            "method": req,
        }

        if params is not None:
            d["params"] = params

        if ident is not None:
            d["id"] = ident

        return json.dumps(d)

    async def _fetch(self, session, req):
        try:
            with async_timeout.timeout(5):
                async with session.post(self._url, headers=self._headers, data=req) as response:
                    return await response.text()
        except asyncio.TimeoutError:
            raise RPCTimeoutError
        except aiohttp.client_exceptions.ClientOSError:
            raise RPCConnectionError

    @staticmethod
    async def _json_loads(j):
        return json.loads(j)

    async def request(self, method, params=None, ident=None, callback=None):
        async with aiohttp.ClientSession() as session:
            req = await self._craft_request(method, params, ident)
            j = await self._fetch(session, req)
            d = await self._json_loads(j)

            try:
                error = d["error"]
            except KeyError:
                raise RPCContentError("RPC response seems malformed (no error field)")

            if error is not None:
                # TODO: pass the error up the stack; tweak RPCError
                raise RPCContentError("RPC response returned error {}".format(error))

            try:
                result = d["result"]
            except KeyError:
                raise RPCContentError("RPC response seems malformed (no result field)")

            if result is None:
                # Is there a case in which a query can return None?
                raise RPCContentError("RPC response returned a null result")

            return d
