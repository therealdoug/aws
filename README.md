# s3_wccp_bypass

Many enterprises make use of a proxy server to filter/cache traffic destined for the internet.  Some enterprises make use of direct connections to Cloud services such as AWS.

WCCP is a protocol used to redirect specific traffic (usually web traffice) destined for the internet through the corporate proxies.  

### The Problem

Directing cloud services through your internet edge stack can compound and exaust resources such as NAT/PAT pools, egress links, and connections per second thresholds. 

Static/SSL bypasses can help aleviate some of this, but your proxies and internet edge is still going to process this information - even if just at the dataplane level.

### A Solution

Using WCCP access-lists, you can redirect or allow certain traffic through a cloud stack to bypass your proxies completely.

Keeping up with changing cloud IPs is a pretty daunting task and prone to 'copy paste' errors.  

This solution aims to reduce the administrative overhead of making an access control list for wccp.

## Playbook walkthrough

```yaml
  vars:
    aws_ips: "https://ip-ranges.amazonaws.com/ip-ranges.json"
    dest_file: "ip-ranges.json"
    acl_name: "web_proxy_redirect"
    group_list: "web_proxy_group"
    wccp_num: "199"
    aws_regions:
      - "us-east-1"
      - "us-east-2"
    aws_service: "S3"
    source_hosts: 
      - "10.1.1.1"
      - "10.2.2.2"
      - "10.3.3.3"
      - "10.4.4.4"
```


1. Download copy of ip-ranges.json from AWS and save it to file
    1. **get_url** module doesn't return the data to a variable, so have to store it to file.
2. Read the file back in:

The following code block does most of the work.  It combines inline Jinja2 template code to generate a `jmespath` query string.  When applied against the aws_ranges variable, it will return the `ip_prefix` attribute from the `ip-ranges.json` file for the regions specified and S3.

Example from `ip-ranges.json`:

```json
  {
      "ip_prefix": "54.231.0.0/17",
      "region": "us-east-1",
      "service": "S3",
      "network_border_group": "us-east-1"
    }
```

3. Set up a jmespath query string based on a list of regions and S3 Service
This code is pretty messy, but the logic is to filter on  
> `(region=(region1 OR region2 ... regionX) AND service="S3")`  

> **NOTE: ** The directive `'>-'` is a yaml block directive for folded block code and allows me to break up the string into multiple lines for *a tiny bit* better readability

```yaml
    - name: "Set query filter to get S3 buckets in listed regions [var: aws_regions]"
      set_fact:
        test_region: >-
          prefixes[?({% for region in aws_regions%}{% if loop.last %}region==`{{ region }}`
          {% else %}region==`{{ region }}`||{% endif %}{% endfor %})&&(service==`{{ aws_service }}`)].ip_prefix
```

> The resultant string will look something like:
> 
```
prefixes[?(region==`us-east-1`||region==`us-east-2` )&&( service==`S3`)].ip_prefix
```

Once applied, the resultant list should be a list like:

```json
[
    "3.5.16.0/21",
    "54.231.0.0/17",
    "52.219.96.0/20",
    "3.5.132.0/23",
    "52.92.16.0/20",
    "52.219.80.0/20",
    "3.5.0.0/20",
    "3.5.128.0/22",
    "52.92.76.0/22",
    "52.216.0.0/15"
]
```

1. Register a new variable with the filtered AWS S3 List, Source host list, name of the WCCP redirect ACL, and the WCCP number
   
```yaml
    - name: Register Variables
      set_fact:
        iprange:
          acl_name: "{{ acl_name }}"
          group_list: "{{ group_list }}"
          wccp_num: "{{ wccp_num }}"
          s3_list: "{{ aws_ipranges|json_query(test_region) }}"
          source: "{{ source_hosts }}"
```

At this point, the var `iprange` will be made available to the jinja template `acl_template.j2` to generate a simple workplan that can be cut/paste into a router

```
!#
!# Remove ACL from WCCP
!# 
no ip wccp 99 redirect-list web_proxy_redirect group-list web_proxy_group
!#
!# Remove ACL
!# 
no ip access-list extended web_proxy_redirect
!#
!# Re-Create ACL with new objects
!#
ip access-list extended web_proxy_redirect
 remark ===== SOURCE HOST - 10.1.1.1 =====
 deny tcp host 10.1.1.1 3.5.16.0 255.255.248.0 eq 443
 deny tcp host 10.1.1.1 54.231.0.0 255.255.128.0 eq 443
 deny tcp host 10.1.1.1 52.219.96.0 255.255.240.0 eq 443
 deny tcp host 10.1.1.1 3.5.132.0 255.255.254.0 eq 443
 deny tcp host 10.1.1.1 52.92.16.0 255.255.240.0 eq 443
 deny tcp host 10.1.1.1 52.219.80.0 255.255.240.0 eq 443
 deny tcp host 10.1.1.1 3.5.0.0 255.255.240.0 eq 443
 deny tcp host 10.1.1.1 3.5.128.0 255.255.252.0 eq 443
 deny tcp host 10.1.1.1 52.92.76.0 255.255.252.0 eq 443
 deny tcp host 10.1.1.1 52.216.0.0 255.254.0.0 eq 443
 remark ===== SOURCE HOST - 10.2.2.2 =====
 deny tcp host 10.2.2.2 3.5.16.0 255.255.248.0 eq 443
 <... config removed for brevity ...>
```