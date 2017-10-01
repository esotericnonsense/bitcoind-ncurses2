# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php

VERSION_STRING = "bitcoind-ncurses v0.2.0-dev"

# MODES = [
#     "monitor", "wallet", "peers", "block",
#     "tx", "console", "net", "forks",
# ]
MODES = ["monitor", "peers", "wallet", "block", "transaction", "net"]
DEFAULT_MODE = "monitor"

# TX_VERBOSE_MODE controls whether the prevouts for an input are fetched.
# TX_VERBOSE_MODE = True
TX_VERBOSE_MODE = False

MIN_WINDOW_SIZE = (10, 20)
