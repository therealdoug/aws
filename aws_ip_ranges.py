#!/usr/bin/python

''' #### Module Documentation: ####
  - jmespath: http://jmespath.org/
  - netaddr: https://netaddr.readthedocs.io/en/latest/index.html
'''

import string, json, jmespath, requests, re, pprint
from netaddr import *

### Variables
_url = "https://ip-ranges.amazonaws.com/ip-ranges.json"
_query = "prefixes[?(region=='us-east-1'||region=='us-east-2')&& \
        (service=='S3')].ip_prefix"

_aws_ranges = requests.get(_url, verify=False)
### End Variables

if (_aws_ranges.status_code == 200):
    _json_ranges = _aws_ranges.json()
    _aws_s3_ranges = jmespath.search(_query,_json_ranges)
    print _aws_s3_ranges
else:
    print "Something went wrong. Status code\r <%s>" % (_aws_ranges.status_code)

for _range in _aws_s3_ranges:
    ip = IPNetwork(_range)
    ip_range = IPRange(ip.network,ip.broadcast)
    print "%s\t\t%s\t\t%s" % (_range,ip.netmask,ip.hostmask)