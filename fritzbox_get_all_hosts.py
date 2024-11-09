#!/usr/bin/python
import logging
from logging import debug, info, warning, error, fatal
import sys
from configargparse import ArgumentParser

# from configparser import ConfigParser
from time import sleep
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts


def main():
    parser = ArgumentParser()

    grp = parser.add_argument_group("Logging")
    grp.add_argument("-q", "--quiet", action="store_true", help="Decrease verbosity.")
    grp.add_argument("-d", "--debug", action="store_true", help="Increase verbosity.")
    grp.add_argument(
        "-j",
        "--journal",
        action="store_true",
        help="Log to systemd journal, not stderr.",
    )

    grp = parser.add_argument_group("Fritz!Box")
    grp.add_argument(
        "-a",
        "--fritzbox_address",
        type=str,
        metavar="IP/addr",
        help="IP address or hostname of Fritz!Box, defaults from configfile.",
    )

    args = parser.parse_args()

    lvl = logging.INFO
    if args.quiet:
        lvl = logging.WARNING
    if args.debug:
        lvl = logging.DEBUG
    logging.basicConfig(level=lvl, format="%(asctime)-15s %(message)s")

    fc = None
    connection_attempts = 5

    while connection_attempts and fc is None:
        try:
            fc = FritzConnection(
                address=args.fritzbox_address  # , password=args.fritzbox_password
            )
            info(f"Connection established to {fc.address}.")
        except Exception as exc:
            error(f"Cannot establish connection: {repr(exc)}")
            connection_attempts -= 1
            if connection_attempts:
                info(f"{connection_attempts} attempts remaining...")
                sleep(5.0)

    if fc is None:
        error(f"Could not establish connetion to Fritz!Box. Exiting.")
        sys.exit(1)

    fh = FritzHosts(fc)

    num_hosts = fh.host_numbers
    info(f"{num_hosts} hosts registered")

    print(
        "#--:-----------------:---------------:-------:--------------------------------:------"
    )
    print(
        "#N : mac             : ip            : dhcp? : hostname                       : status"
    )
    print(
        "#--:-----------------:---------------:-------:--------------------------------:------"
    )

    for n in range(0, num_hosts):
        host = fh.get_generic_host_entry(n)
        ip = host.get("NewIPAddress", "?")
        addrtype = host.get("NewAddressSource", "?")
        name = host.get("NewHostName", "?")
        mac = host.get("NewMACAddress", "?")
        status = host.get("NewActive", "?")
        print(f"{n:<3} {mac:<17} {ip:<15} {addrtype:<7} {name:<32} {status}")

    print(
        "#--:-----------------:---------------:-------:--------------------------------:------"
    )


if __name__ == "__main__":
    main()
