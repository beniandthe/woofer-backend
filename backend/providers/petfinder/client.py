import requests
from typing import Dict, Iterator, Optional


class PetfinderError(Exception):
    pass


class PetfinderAuthError(PetfinderError):
    pass


class PetfinderClient:
    """
    Read-only Petfinder API client.
    No knowledge of Woofer models.
    """

    BASE_URL = "https://api.petfinder.com/v2"

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self._access_token: Optional[str] = None

    # ---------- Auth ----------

    def authenticate(self) -> None:
        resp = requests.post(
            f"{self.BASE_URL}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
            timeout=self.timeout,
        )

        if resp.status_code != 200:
            raise PetfinderAuthError("Failed to authenticate with Petfinder")

        payload = resp.json()
        self._access_token = payload.get("access_token")

        if not self._access_token:
            raise PetfinderAuthError("Petfinder token missing in response")

    # ---------- Internal request ----------

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        if not self._access_token:
            self.authenticate()

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

        resp = requests.get(
            f"{self.BASE_URL}{path}",
            headers=headers,
            params=params or {},
            timeout=self.timeout,
        )

        if resp.status_code == 401:
            # token expired, retry once
            self.authenticate()
            return self._get(path, params)

        if resp.status_code >= 400:
            raise PetfinderError(f"Petfinder API error {resp.status_code}")

        return resp.json()

    # ---------- Public fetchers ----------

    def iter_organizations(self, limit: int = 100) -> Iterator[Dict]:
        page = 1

        while True:
            data = self._get(
                "/organizations",
                params={"limit": limit, "page": page},
            )

            orgs = data.get("organizations", [])
            for org in orgs:
                yield org

            pagination = data.get("pagination", {})
            if page >= pagination.get("total_pages", 1):
                break

            page += 1

    def iter_pets(self, limit: int = 100, organization: Optional[str] = None) -> Iterator[Dict]:
        page = 1

        params = {"limit": limit}
        if organization:
            params["organization"] = organization

        while True:
            params["page"] = page
            data = self._get("/animals", params=params)

            animals = data.get("animals", [])
            for animal in animals:
                yield animal

            pagination = data.get("pagination", {})
            if page >= pagination.get("total_pages", 1):
                break

            page += 1
