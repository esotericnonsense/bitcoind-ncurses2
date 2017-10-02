# bitcoind-ncurses2 v0.3.1

Python ncurses front-end for bitcoind. Uses the JSON-RPC API.

![ScreenShot](/img/bitcoind-ncurses2.gif)

- esotericnonsense (Daniel Edgecumbe)

## Dependencies

* Developed with python 3.6.2, Bitcoin Core 0.15.0.1
* PyPi packages: aiohttp and async-timeout (see requirements.txt)

## Features

* Updating monitor mode showing bitcoind's status, including:
* Current block information: hash, height, fees, timestamp, age, diff, ...
* Basic block explorer with fast seeking, no external DB required
* Basic transaction viewer with fast seeking, best with -txindex=1
* Ability to query blocks by hash, height; transactions by txid
* Wallet transaction and balance viewer
* Charting network monitor
* Peer/connection information
* Basic debug console functionality

## Installation and usage

```
git clone https://github.com/esotericnonsense/bitcoind-ncurses2
```

```
pip3 install -r bitcoind-ncurses2/requirements.txt
```
or, on Arch Linux:
```
pacman -S python-aiohttp python-async-timeout
```

```
cd bitcoind-ncurses2
python3 main.py
```

bitcoind-ncurses2 will automatically use the cookie file available in
~/.bitcoin/, or the RPC settings in ~/.bitcoin/bitcoin.conf. To use a different
datadir, specify the --datadir flag:

```
python3 main.py --datadir /some/path/to/your/datadir
```

This is an early development release and a complete rewrite of the original
bitcoind-ncurses. Expect the unexpected.

Feedback
--------

Please report any problems using the Github issue tracker. Pull requests are
also welcomed.
The author, esotericnonsense, can often be found milling around on #bitcoin
(Freenode).

Donations
---------

If you have found bitcoind-ncurses2 useful, please consider donating.

All funds go towards the operating costs of my hardware and future
Bitcoin development projects.

![ScreenShot](/img/3BYFucUnVNhZjUDf6tZweuZ5r9PPjPEcRv.png)

**bitcoin 3BYFucUnVNhZjUDf6tZweuZ5r9PPjPEcRv**
