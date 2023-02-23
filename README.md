# fritzbox_dyndns_update

perform dyndns updates, get address from your Fritz!Box

This script can query your Fritz!Box for its external addresses and update
your dynamic DNS. Example for he.net:


# Usage

    usage: fritzbox_dyndns_update.py [-h] [-n] [-q] [-d] [-s SEC]
                                     [--config CONFIG] [--no-ipv4] [-6]
                                     [--ipv6-suffix IPV6_SUFFIX] [-a IP/addr]
                                     [-p passwd] [-U URL] [-P passwd]
                                     [-H hostname]
    
    options:
      -h, --help            show this help message and exit
    
    Program Control:
      -n, --dry-run
      -q, --quiet
      -d, --debug
      -s SEC, --sleep SEC   Sleep SEC seconds between checks [def: 60]
      --config CONFIG       Config file [def: /etc/fritzconneciton.ini]
      --no-ipv4             Skip IPv4 (default: only v4)
      -6, --ipv6            Enable IPv6 (default: only v4)
      --ipv6-suffix IPV6_SUFFIX
                            Specify ::1:2/32 to replace, e.g. the lowest 32 bits
                            with the given bits.
    
    Fritz!Box:
      -a IP/addr, --fritzbox_address IP/addr
                            IP address or hostname of Fritz!Box, defaults from
                            configfile.
      -p passwd, --fritzbox_password passwd
                            Password for UI on Fritz!Box, defaults from
                            configfile.
    
    DynDNS:
      -U URL, --dyndns_url URL
                            DynDNS URL, default from configfile.
      -P passwd, --dyndns_password passwd
                            DynDNS URL, default from configfile.
      -H hostname, --dyndns_hostname hostname
                            DynDNS URL, default from configfile.
    
    Args that start with '--' (eg. -n) can also be set in a config file (specified
    via --config). Config file syntax allows: key=value, flag=true, stuff=[a,b,c]
    (for details, see syntax at https://goo.gl/R74nmi). If an arg is specified in
    more than one place, then commandline values override config file values which
    override defaults.
    
# Example config file

    fritzbox_address=172.17.2.1
    fritzbox_password=FRITZBOX_UI_PASSWORD
    
    dyndns_url=https://dyn.dns.he.net/nic/update
    dyndns_hostname=dillberg.com
    dyndns_password=DYNDNS_PASSWORD
