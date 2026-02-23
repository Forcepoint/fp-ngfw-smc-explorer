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

# -*- coding: utf-8 -*-
"""low level api. wrapper on top of requests.session with addition of
   smc login and logout methods

"""

import urllib3
import logging
import tempfile
import requests
import os

from urllib.parse import urlparse, urlunparse
from .exceptions import InvalidSessionError, SMCOperationFailure

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_id_from_url(url):
    """
    url=http://192.168.100.7:8082/6.8/elements/network/373
    returns network/373
    """
    (_, _, path, *rest) = urlparse(url)
    path_parts = path.split("/")[3:]
    resource_id = "/".join(path_parts)
    logger.debug("get_id_from_url: path=%s", resource_id)
    return resource_id


class SMCSession(object):
    """
    rest client: wrapper of requests
    """

    def __init__(
        self,
        url: str,
        ver: str,
        apikey: str,
        cert: str | None = None,
        verify_ssl: bool = False,
        domain: str = "Shared Domain",
    ):
        self.url = url
        self.ver = ver
        self.apikey = apikey
        self.domain = domain
        self.verify_ssl = verify_ssl
        self.cert = cert

        if cert:
            self.cert_temp_file = tempfile.NamedTemporaryFile(delete=False)
            self.cert_temp_file.write(cert.encode("ascii"))
            self.cert_temp_file.close()
            logger.info("temp file=%s", self.cert_temp_file.name)

        self._session = requests.Session()

    def make_url(self, path):
        url_parts = list(urlparse(self.url))
        path_part = os.path.join(self.ver, path)
        url_parts[2] = path_part
        url = urlunparse(url_parts)
        return url

    @staticmethod
    def _format_error(resp):
        """extract error message from http response

        :returns: (message, detail)
        :rtype: tuple

        """
        message = ""
        details = ""
        if not resp.headers:
            message = "Error {}".format(resp.status_code)
            return (message, details)

        content_type = resp.headers.get("content-type")
        if not content_type:
            message = "Error {}".format(resp.status_code)
            return (message, details)

        if content_type.startswith("application/json"):
            try:
                data = resp.json()
            except ValueError:
                message = "Error {}".format(resp.status_code)
            else:
                message = data.get("message", None)
                details = data.get("details", None)
                if isinstance(details, list):
                    details = " ".join(details)


        elif resp.text:
            message = resp.text

        if not message:
            message = "Error {}".format(resp.status_code)

        return (message, details)

    @staticmethod
    def _check_response(method, resp):
        """
        raise SMCOperationFailure on error
        """
        method = method.upper()
        success_status = {
            "GET": (200, 204, 304),
            "POST": (200, 201, 202),
            "PUT": (
                200,
                204,
            ),
            "DELETE": (200, 204),
        }

        status_code = resp.status_code
        if status_code in success_status[method]:
            return True

        (message, details) = SMCSession._format_error(resp)
        logger.error(
            "HTTP response error: status=%s, message=%s, details=%s",
            resp.status_code,
            message,
            details,
        )
        if details:
            raise SMCOperationFailure(message, details)
        else:
            raise SMCOperationFailure(message)

    # pylint: disable=too-many-arguments
    def request(
        self, method, url, params=None, data=None, headers=None, json=None, **kwargs
    ):
        """
        raises SMCOperationFailure/InvalidSessionError
        """
        res = None

        if url is None:
            raise ValueError("url is null")

        verify = False

        if self.cert:
            verify = self.cert_temp_file.name

        # we do not verify ssl even if a cert is provided
        if not self.verify_ssl:
            verify=False

        logger.debug("request: method=%s, url=%s", method, url)
        res = self._session.request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            json=json,
            **kwargs,
            verify=verify,
        )

        if res.status_code == 401:
            raise InvalidSessionError("not logged in or session expired")
        else:
            SMCSession._check_response(method, res)
        return res

    def get(self, url, **kwargs):
        """see requests module"""
        kwargs.setdefault("allow_redirects", True)
        return self.request("GET", url, **kwargs)

    # def get(self, url, data=None, json=None, **kwargs):
    #     """see requests module """
    #     kwargs.setdefault('allow_redirects', True)
    #     return self.request('GET', url, data=data, json=json, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """see requests module"""
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        """see requests module"""
        return self.request("PUT", url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        """see requests module"""
        return self.request("DELETE", url, **kwargs)

    def login(self):
        """ """
        login_url = self.make_url("login")
        res = self.post(
            login_url,
            json={"domain": self.domain, "authenticationkey": self.apikey},
        )
        return res

    def logout(self):
        """ """
        logout_url = self.make_url("logout")
        res = self.put(logout_url)
        return res

    def destroy(self):
        if hasattr(self, "cert_temp_file"):
            logger.info("destroying temp file=%s", self.cert_temp_file.name)
            os.unlink(self.cert_temp_file.name)
