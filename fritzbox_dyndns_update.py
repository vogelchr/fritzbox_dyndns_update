#!/usr/bin/python
import logging
from logging import debug, info, warning, error, fatal
import sys
from configargparse import ArgumentParser
#from configparser import ConfigParser
from time import sleep
from urllib.request import urlopen
from urllib.parse import urlencode
from pathlib import Path
from fritzconnection import FritzConnection

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

    grp = parser.add_argument_group('Program Control')
    grp.add_argument('-q', '--quiet', action='store_true')
    grp.add_argument('-d', '--debug', action='store_true')
    grp.add_argument('-s', '--sleep', type=int, default=60,
                     metavar='SEC',
                     help='Sleep SEC seconds between checks [def: %(default)d]')
    grp.add_argument('--config', type=Path,
                     is_config_file=True,
                     default='/etc/fritzconneciton.ini',
                     help='Config file [def: %(default)s]')

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

    logging.basicConfig(level=lvl, format='%(asctime)-15s %(message)s')

    if args.fritzbox_password is None:
        print('You need to specify the password in the config file or on the command line!')
        sys.exit(1)

    fc = FritzConnection(address=args.fritzbox_address,
                         password=args.fritzbox_password)

    last_ipv4 = None
    first_round = True

    while True:
        if first_round:
            first_round = False
        else:
            debug(f'Sleeping for {args.sleep} seconds.')
            sleep(args.sleep)

        this_ipv4 = None
        try:
            ipv4_ret = fc.call_action('WANIPConn', 'GetExternalIPAddress')
            this_ipv4 = ipv4_ret['NewExternalIPAddress'].strip().lower()
        except Exception as exc:
            warning(f'Exception {repr(exc)} raised during Fritz!BOX query.')

#       for when we want to support ipv6
#        ipv6_ret = fc.call_action('WANIPConn', 'X_AVM_DE_GetExternalIPv6Address')
#        this_ipv6 = ipv6_ret['NewExternalIPv6Address'].strip().lower()

        if not this_ipv4 or this_ipv4 == last_ipv4:
            if this_ipv4 is None:
                warning(f'IPv4 address is not known.')
            else:
                debug(f'IPv4 address is {last_ipv4} (unchanged).')
            continue

        # now update...
        if this_ipv4 and this_ipv4 != last_ipv4:
            # this branch updates
            if last_ipv4 is None:
                info(f'IPv4 address is {this_ipv4} (initial).')
            else:
                info(
                    f'IPv4 address is {this_ipv4}, was {last_ipv4} (changed).')

        try:
            update_payload = urlencode({'hostname': args.dyndns_hostname,
                                        'password': args.dyndns_password, 'myip': this_ipv4}).encode('ascii')
            debug(f'POST to {args.dyndns_url} with payload {update_payload}.')
            resp = urlopen(args.dyndns_url, update_payload)
            content = resp.read().strip().decode('ascii')
            debug(f'POST result code {resp.code}, content: {content}')

            status, *_ = content.split()
            status = status.lower().strip()

            if resp.code == 200 and status in ['good', 'nochg']:
                debug(f'Good update.')
                last_ipv4 = this_ipv4

        except Exception as exc:
            warning(f'Exception {repr(exc)} raised during DDNS update!')


if __name__ == "__main__":
    main()
