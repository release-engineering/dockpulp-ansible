"""Manages all access to Pyxis."""
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.util.retry import Retry

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Pyxis(object):
    """This class can be used to retrieve data from Pyxis."""

    def __init__(self, url, cert=()):
        """Constructor."""
        self._pyxis_url = url
        self._pyxis_api_v1_url = "/".join([self._pyxis_url, "v1/"])
        self._session = self._get_pyxis_session(cert=cert)

    def _get_pyxis_session(self, cert=()):
        """Prepare a requests session to Pyxis.

        Returns: the session object.
        """
        session = requests.session()
        retry = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        # session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        session.cert = cert
        return session

    def _pyxis_request(self, url_fragment, page=None, page_size=None):
        """Pyxis JSON API GET request.

        Args:
            url_fragment - API url_fragment

            page         - The page number to start accessing.
                           If set, you MUST also include page_size!

            page_size    - The page size to get (recommend 100).
                           If set you MUST also include page!

        Returns:
            A dictionary as returned from response.json() for  non-paginated
            data. For paginated data, the return value is json()'d, and all
            pages are joined together into a single list.

        """
        headers = {"Accept": "application/json"}
        url = self._pyxis_api_v1_url + url_fragment
        if page is not None:
            url += "?page=%s&page_size=%s" % (page, page_size)

        result = self._session.get(url, headers=headers)
        result.raise_for_status()
        data = result.json()

        # Return non-paginated data now
        if page is None:
            return data

        # If there is more than one page, loop through remaining pages
        all_data = data["data"]
        if data["total"] > page_size:

            # figure out how many pages there are
            pages = int(data["total"] / page_size)
            pages += 1 if data["total"] % page_size > 0 else 0

            # get remaining pages
            for page in range(1, pages):
                url = self._pyxis_api_v1_url + url_fragment
                url += "?page=%s&page_size=%s" % (page, page_size)
                result = self._session.get(url, headers=headers)
                result.raise_for_status()
                all_data.extend(result.json()["data"])
        return all_data

    def get_all_repositories(self):
        url = "repositories"
        return self._pyxis_request(url, 0, 100)

    def get_repository(self, registry, repository):
        url = "repositories/registry/%s/repository/%s" % (registry, repository)
        try:
            return self._pyxis_request(url)
        except requests.exceptions.HTTPError:
            return {}

    def get_repository_by_id(self, id):
        url = "repositories/id/%s" % id
        return self._pyxis_request(url)

    def patch_repository(self, id, repository):
        headers = {"Accept": "application/json"}
        url = self._pyxis_api_v1_url + "repositories" + "/id/{}".format(id)
        response = self._session.patch(url, json=repository, headers=headers)
        return response

    def post_repository(self, repository):
        headers = {"Accept": "application/json"}
        url = self._pyxis_api_v1_url + "repositories"
        response = self._session.post(url, json=repository, headers=headers)
        return response

    def get_all_product_listings(self):
        url = "product-listings"
        return self._pyxis_request(url, 0, 100)

    def get_product_listings_by_id(self, id):
        url = "product-listings/id/%s" % id
        try:
            return self._pyxis_request(url)
        except requests.exceptions.HTTPError:
            return {}

    def patch_product_listing(self, id, product_listing):
        headers = {"Accept": "application/json"}
        url = self._pyxis_api_v1_url + "product-listings" + "/id/{}".format(id)
        response = self._session.patch(url, json=product_listing, headers=headers)
        return response

    def post_product_listing(self, product_listing):
        headers = {"Accept": "application/json"}
        url = self._pyxis_api_v1_url + "product-listings"
        response = self._session.post(url, json=product_listing, headers=headers)
        return response

    def get_all_teams(self):
        url = "teams"
        return self._pyxis_request(url, 0, 100)

    def get_team_by_id(self, id):
        url = "teams/id/%s" % id
        return self._pyxis_request(url)
