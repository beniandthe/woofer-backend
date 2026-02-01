from django.test import SimpleTestCase
from unittest import mock

from providers.petfinder.client import PetfinderClient


def mock_token_response(*args, **kwargs):
    class R:
        status_code = 200
        def json(self):
            return {"access_token": "fake-token"}
    return R()


def mock_orgs_response(*args, **kwargs):
    class R:
        status_code = 200
        def json(self):
            return {
                "organizations": [{"id": "org1"}, {"id": "org2"}],
                "pagination": {"total_pages": 1},
            }
    return R()


class PetfinderClientTests(SimpleTestCase):
    @mock.patch("requests.post", side_effect=mock_token_response)
    @mock.patch("requests.get", side_effect=mock_orgs_response)
    def test_iter_organizations(self, mock_get, mock_post):
        client = PetfinderClient("key", "secret")
        orgs = list(client.iter_organizations())
        self.assertEqual(len(orgs), 2)
        self.assertEqual(orgs[0]["id"], "org1")

