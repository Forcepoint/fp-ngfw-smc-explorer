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
high level api based on Element.
"""

import logging
from jmespath import search as jp
import json

from smc_explorer.exceptions import ResolveError
from smc_explorer.hname import resolve_hname

from .smc_element import SMCElementJson
from .smc_session import SMCSession

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


class SMCClient(object):
    """
    high level api to access the smc rest api based on Element
    """

    def __init__(self, session: SMCSession):
        """constructor

        Args:
            session (SMCSession): low level request object

        """

        self._session = session

    @property
    def session(self):
        return self._session


    def get(self, hname: str) -> SMCElementJson:
        """return an SMCElementJson corresponding to the given hname
        eg
        get("#single_fw/fw1")

        :returns: SMCElementJson with data containing parsed json
        :rtype: SMCElementJson

        """
        try:
            target_href = resolve_hname(self._session, hname)
        except ResolveError as err:
            raise err

        headers = {"Accept": "application/json"}
        res = self._session.get(target_href, headers=headers)
        # todo err

        etag = res.headers.get("ETag")
        data = json.loads(res.text)
        return SMCElementJson(data, hname, etag)

    def list(self, hname=None):
        """
        return a list of names below the given hname

        e.g.

        list("#single_fw")
        returns
        ["fw1", "fw2"]
        """
        res = []
        if not hname:
            # list top-level resources
            api_url = self._session.make_url("api")
            api_url_res = self._session.get(api_url)
            api_url_res_json = api_url_res.json()
            res = [e["rel"] for e in api_url_res_json["entry_point"]]
            return res

        smc_element = self.get(hname)
        res = jp("result[*].name", smc_element.data)

        if not res:
            res = jp("link[*].rel", smc_element.data)
        return res or []

    def delete(self, target):
        """delete an element. You need to pass the SMCElement, because
        deletion requires an etag

        Parameters:
        target - either an SMCElement or an hname/href
        """
        # todo error

        if isinstance(target, SMCElementJson):
            smc_element = target
        else:
            smc_element = self.get(target)

        target_href = resolve_hname(self._session, smc_element.hname)

        # todo refresh etags if object has changed
        resp = self._session.delete(target_href, headers={"If-Match": smc_element.etag})
        logger.debug("status_code=%d", resp.status_code)
        logger.debug("text=%s", resp.text)
