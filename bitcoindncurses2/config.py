# Copyright (c) 2014-2017 esotericnonsense (Daniel Edgecumbe)
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/licenses/mit-license.php


def parse_file(filename):
    with open(filename, "r") as f:
        cfg = {}
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    # replace maintains compatibility with older config files
                    (key, value) = line.replace(' = ', '=').split('=', 1)
                    cfg[key] = value
                except ValueError:
                    # Happens when line has no '=', ignore
                    pass

    return cfg
