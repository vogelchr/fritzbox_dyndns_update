#!/usr/bin/python
import logging
from logging import debug, info, warning, error, fatal
import sys
from configargparse import ArgumentParser
# from configparser import ConfigParser
from time import sleep
from urllib.request import urlopen
from urllib.parse import urlencode
from pathlib import Path
from fritzconnection import FritzConnection
from ipaddress import IPv6Address, IPv6Interface


def merge_v6_addr_sfx(addr: IPv6Address, sfx: IPv6Interface) -> IPv6Address:
    addr_b = addr.packed
    sfx_b = sfx.packed
    nm_b = sfx.netmask.packed
    merged_b = bytes([(a & n) | (s & ~n)
                     for a, s, n in zip(addr_b, sfx_b, nm_b)])

    return IPv6Address(merged_b)

# def print_status(fs):
#    print("FritzStatus:\n")
#    status_informations = [
#        ("is linked", "is_linked"),
#        ("is connected", "is_connected"),
#        ("external ip (v4)", "external_ip"),
#        ("external ip (v6)", "external_ipv6"),
#        ("internal ipv6-prefix", "ipv6_prefix"),
#        ("uptime", "str_uptime"),
#        ("bytes send", "bytes_sent"),
#        ("bytes received", "bytes_received"),
#        ("max. bit rate", "str_max_bit_rate"),
#    ]
#    for status, attribute in status_informations:
#        try:
#            information = getattr(fs, attribute)
#        except (FritzServiceError, FritzActionError):
#            information = f'unsupported attribute "{attribute}"'
#        print(f"    {status:22}: {information}")
#    print()


def main():
    parser = ArgumentParser()

    grp = parser.add_argument_group('Logging')
    grp.add_argument('-q', '--quiet', action='store_true',
                     help='Decrease verbosity.')
    grp.add_argument('-d', '--debug', action='store_true',
                     help='Increase verbosity.')
    grp.add_argument('-j', '--journal', action='store_true',
                     help='Log to systemd journal, not stderr.')

    grp = parser.add_argument_group('Program Control')
    grp.add_argument('-n', '--dry-run', action='store_true')
    grp.add_argument('-s', '--sleep', type=int, default=60,
                     metavar='SEC',
                     help='Sleep SEC seconds between checks [def: %(default)d]')
    grp.add_argument('--config', type=Path,
                     is_config_file=True,
                     default='/etc/fritzconneciton.ini',
                     help='Config file [def: %(default)s]')
    grp.add_argument('--no-ipv4', action='store_true',
                     help='Skip IPv4 (default: only v4)')
    grp.add_argument('-6', '--ipv6', action='store_true',
                     help='Enable IPv6 (default: only v4)')
    grp.add_argument('--ipv6-suffix', type=IPv6Interface,
                     help='Specify ::1:2/32 to replace, e.g. the lowest 32 bits with the given bits.')

    grp = parser.add_argument_group('Fritz!Box')
    grp.add_argument('-a', '--fritzbox_address', type=str,
                     metavar='IP/addr',
                     help='IP address or hostname of Fritz!Box, defaults from configfile.')
    grp.add_argument('-p', '--fritzbox_password', type=str,
                     metavar='passwd',
                     help='Password for UI on Fritz!Box, defaults from configfile.')

    grp = parser.add_argument_group('DynDNS')
    grp.add_argument('-U', '--dyndns_url', type=str,
                     metavar='URL',
                     help='DynDNS URL, default from configfile.')
    grp.add_argument('-P', '--dyndns_password', type=str,
                     metavar='passwd',
                     help='DynDNS URL, default from configfile.')
    grp.add_argument('-H', '--dyndns_hostname', type=str,
                     metavar='hostname',
                     help='DynDNS URL, default from configfile.')

    args = parser.parse_args()

    lvl = logging.INFO
    if args.quiet:
        lvl = logging.WARNING
    if args.debug:
        lvl = logging.DEBUG

    if args.journal:
        from systemd.journal import JournalHandler
        handler = JournalHandler(SYSLOG_IDENTIFIER=Path(__file__).stem)
        logging.basicConfig(
            level=lvl, format='%(message)s', handlers=[handler])
    else:
        logging.basicConfig(level=lvl, format='%(asctime)-15s %(message)s')

    if args.fritzbox_password is None:
        print('You need to specify the password in the config file or on the command line!')
        sys.exit(1)

    fc = None
    connection_attempts = 5

    while connection_attempts and fc is None:
        try:
            fc = FritzConnection(address=args.fritzbox_address,
                                 password=args.fritzbox_password)
            info(f'Connection established to {args.fritzbox_address}.')
        except Exception as exc:
            error(f'Cannot establish connection: {repr(exc)}')
            connection_attempts -= 1
            if connection_attempts:
                info(f'{connection_attempts} attempts remaining...')
                sleep(5.0)

    if fc is None:
        error(f'Could not establish connetion to Fritz!Box. Exiting.')
        sys.exit(1)

    last_by_family = dict()
    first_round = True

    while True:
        if first_round:
            first_round = False
        else:
            debug(f'Sleeping for {args.sleep} seconds.')
            sleep(args.sleep)

        for family in ['ipv4', 'ipv6']:

            if family == 'ipv4' and args.no_ipv4:
                continue
            if family == 'ipv6' and not args.ipv6:
                continue

            this_addr = None
            if not family in last_by_family:
                last_by_family[family] = None

            try:
                if family == 'ipv4':
                    ret = fc.call_action('WANIPConn', 'GetExternalIPAddress')
                    this_addr = ret['NewExternalIPAddress'].strip().lower()
                else:
                    ret = fc.call_action(
                        'WANIPConn', 'X_AVM_DE_GetExternalIPv6Address')
                    this_addr = ret['NewExternalIPv6Address'].strip().lower()
            except Exception as exc:
                warning(
                    f'Exception {repr(exc)} raised during Fritz!BOX query.')

            if not this_addr:
                warning(f'{family} address is not known.')
                continue

            if this_addr == last_by_family[family]:
                debug(
                    f'{family} address is {last_by_family[family]} (unchanged).')
                continue

            if last_by_family[family] is None:
                info(f'{family} address is {this_addr} (initial).')
            else:
                info(
                    f'{family} address is {this_addr}, was {last_by_family[family]} (changed).')

            update_addr = this_addr
            if args.ipv6_suffix is not None and family == 'ipv6':
                update_addr = merge_v6_addr_sfx(
                    IPv6Address(this_addr), args.ipv6_suffix).compressed
                info(f'{family} suffix changes {this_addr} -> {update_addr}')

            if args.dry_run:
                info(f'Dry run, would update {family} to {update_addr}.')
                last_by_family[family] = this_addr
                continue

            try:
                update_payload = urlencode({'hostname': args.dyndns_hostname,
                                            'password': args.dyndns_password, 'myip': update_addr}).encode('ascii')
                debug(
                    f'POST to {args.dyndns_url} with payload {update_payload}.')
                resp = urlopen(args.dyndns_url, update_payload)
                content = resp.read().strip().decode('ascii')
                debug(f'POST result code {resp.code}, content: {content}')

                status, *_ = content.split()
                status = status.lower().strip()

                if resp.code == 200 and status in ['good', 'nochg']:
                    debug(f'{family}: Good update, status {status}.')
                    last_by_family[family] = this_addr
                else:
                    error(
                        f'{family}: Bad update, resonse code {resp.code} and status {status}.')

            except Exception as exc:
                warning(f'Exception {repr(exc)} raised during DDNS update!')


if __name__ == "__main__":
    main()
