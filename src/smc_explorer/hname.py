#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
"""
translate hname(hierarchical names) into proper urls

main functions:
- resolve_hname
"""

import sys
from pprint import pprint
import re
import logging
from jmespath import search as jp

from .exceptions import ResolveError
from .smc_session import SMCSession

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

# start character of hnames
HNAME_MARKER = "#"

def split_hname(hname: str) -> list:
    """split a hierarchical name (hname) into parts.

    double '/' is used to escape the '/'.
    and is transformed into a into single '/'

    e.g.
        hname = "network/network-fd02:://64"
        => ["network", "network-fd02::/64"]

    :param str hname: hierarchical name
    :returns: a list with the splitted parts of the hname
    :rtype: list
    """
    lst = []
    cat = None
    for part in re.split(r"/(?=[^/])", hname):
        if cat:
            part = cat + part
            cat = None
        if part[-1] == "/":
            cat = part
        else:
            lst.append(part)
    return lst



def get_href_from_results(data: dict, part: str) -> str|None:
    """
    get href from "results_page/result" entries with matching name

    """
    print("todo get_href_from_results unimplemented")
    pprint(data)
    # href = jp("[?name=='" + part + "'].href|[0]", data)
    raise Exception("unimplemented get_href_from_results")
    return _get_href_from_xpath(data, part, "/results_page/result", "name")


def get_href_from_links(data: dict, part: str) -> str|None:
    """
    get href from "links"

    eg
    return href
    """
    href = jp("result[?name=='" + part + "'].href|[0]", data)

    if not href:
        href = jp("link[?rel=='" + part + "'].href|[0]", data)

    return href


def _resolve_hname_with_base_url(session: SMCSession, hname: str, base_url: str|None = None) -> str:
    """

    :param SMCSession session: client to send smc api requests
    :param str hname: hierarchical name to be converted to an
    url. (optionally) starts with '#'
    :param str base_url: (optional) base url to resolve the hname

    :returns: returns the url corresponding to the hname
    :rtype: str

    :raises ResolveError: failed to resolve the hname
    :raises SMCOperationFailure: the smc report an error

    """
    logger.debug("resolving hname=%s,  base_url=%s", hname, base_url)

    hname_parts = split_hname(hname)

    elt = None

    if base_url:
        result_url = base_url
    else:
        elt = hname_parts.pop(0)
        if elt.startswith("system"):
            result_url = session.make_url(elt)
        else:
            result_url = session.make_url("elements/" + elt)

    for i, part in enumerate(hname_parts):
        logger.debug("resolving part=%s, current_url=%s", part, result_url)
        # exceptions of SMCSession are propagated
        resp = session.get(result_url, headers={"Accept": "application/json"})
        data = resp.json()
        result_url = get_href_from_links(data, part)

        if elt == "vpn" and i == 0:
            # special case for vpn. Need to open it first
            try:
                res = session.put(f"{result_url}/unlock", headers={"Accept": "application/json"})
            except Exception as exc:
                print("unlock failed", exc)
            res = session.post(f"{result_url}/open", headers={"Accept": "application/json"})
            logger.debug("vpn open status_code=%s", res.status_code)
            # todo close needed

        # fallback try with jmespath
        if not result_url:
            try:
                result_url = jp(part, data)
            except Exception:
                logger.warning("jmespath failed for part=%s", part)
        # if not result_url:
        #     print("todo 2")
        #     result_url = get_href_from_results(data, part)
        #     sys.exit(0)
        if not result_url:
            raise ResolveError("Cannot resolve hname part '{}'".format(part))

    if result_url is None:
        raise ResolveError("Failed to resolve hname '{}'".format(hname))

    logger.debug("resolved: target_href=%s", result_url)
    return result_url


def resolve_hname(session: SMCSession, hname: str) -> str:
    """return the url corresponding to the hierarchical name (hname)

     if base_url is None, resolution is relative to /{ver}/elements/

     eg
       hname="#fw_policy/fws30policy/fw_ipv6_nat_rules/Rule @2097190.1"
       hname="#log_server/LogServer 192.168.100.7"
       hname = "https://https://192.168.100.7:8085/6.10/elements/single_fw/1234#firewall_node/fw1node/initial_contact"


    :param str hname: hierarchical name to be converted to an
    url. (optionally) starts with '#'

    :param SMCSession session: client to send smc api requests

    :returns: returns the url corresponding to the hname
    :rtype: str

    :raises ResolveError: failed to resolve the hname
    :raises SMCOperationFailure: the smc report an error

    """
    if not hname:
        raise ResolveError("Failed to resolve empty hname")

    rel_hname = None
    base_url = None

    # resolve hname relative to a base_url
    # eg https://https://192.168.100.7:8085/6.10/elements/single_fw/1234#firewall_node/fw1node/initial_contact
    if hname.startswith("http"):
        matchObj = re.match(r"(https?://.+/elements/.+)#(.+)", hname)
        if not matchObj:
            # just a regular http link, nothing to resolve
            return hname
        base_url, rel_hname = matchObj.groups()
    else:
        rel_hname = hname

    if rel_hname[0] == HNAME_MARKER:
        rel_hname = rel_hname[1:]

    if rel_hname[-1] == "/":
        rel_hname = rel_hname[:-1]

    # todo absolute hname not supported (eg #/system/whatever),
    # for now only relative to /{ver}/elements resolved (eg #single_fw)
    # is it needed ?

    res = _resolve_hname_with_base_url(session, rel_hname, base_url)
    return res


def is_hname(text: str) -> bool:
    if not text:
        return False
    if text[0] == HNAME_MARKER:
        return True
    if text.startswith("http"):
        return True
    return False


def parse_hname(text: str) -> tuple[str|None, str|None]:
    """
    hname:
    1. starts with '#'.

    eg
    #fw_policy/fwpol1/fw_ipv4_access_rules/[0]

    2. an url with hname in the fragment part

    eg:
    https://192.168.100.7:8085/6.10/elements/single_fw/1234#firewall_node/fw1node/initial_contact

    returns (hname, base_url)
    eg:
    parse_hname("#fw_policy/fwpol1/fw_ipv4_access_rules/[0]")
    => ("#fw_policy/fwpol1/fw_ipv4_access_rules/[0]", None)

    """
    if not text:
        return (None, None)

    if text[0] == HNAME_MARKER:
        return (text, None)

    if text.startswith("http"):
        matchObj = re.match(r"(https?://.+/elements/.+)#(.+)", text)
        if matchObj:
            base_url, hname = matchObj.groups()
            return (hname, base_url)

    return (None, None)
