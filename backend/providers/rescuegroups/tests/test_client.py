from django.test import SimpleTestCase
from unittest import mock

from providers.rescuegroups.client import RescueGroupsClient


def _mock_resp(json_payload, status=200):
    class R:
        status_code = status
        def json(self):
            return json_payload
        text = "ok"
    return R()


class RescueGroupsClientTests(SimpleTestCase):
    @mock.patch("requests.get")
    def test_iter_orgs_one_page(self, mget):
        mget.return_value = _mock_resp({
            "data": [
                {"id": "1", "type": "orgs", "attributes": {"name": "Org1", "email": "o1@example.com", "city": "LA", "state": "CA"}},
                {"id": "2", "type": "orgs", "attributes": {"name": "Org2"}},
            ],
            "meta": {"pages": 1}
        })

        c = RescueGroupsClient(api_key="k", base_url="https://api.rescuegroups.org/v5")
        orgs = list(c.iter_orgs(limit=10))
        self.assertEqual(len(orgs), 2)
        self.assertEqual(orgs[0].external_org_id, "1")
        self.assertEqual(orgs[0].name, "Org1")

    @mock.patch("requests.get")
    def test_iter_pets_available_dogs(self, mget):
        mget.return_value = _mock_resp({
            "data": [
                {"id": "99", "type": "animals", "attributes": {"name": "Bella", "descriptionText": "Sweet", "sex": "Female", "sizeGroup": "Medium", "ageGroup": "Young Adult", "pictureThumbnailUrl": "https://x/t.jpg"},
                 "relationships": {"orgs": {"data": [{"type": "orgs", "id": "1"}]}}}
            ],
            "meta": {"pages": 1},
            "included": []
        })

        c = RescueGroupsClient(api_key="k", base_url="https://api.rescuegroups.org/v5")
        pets = list(c.iter_pets(limit=5))
        self.assertEqual(len(pets), 1)
        self.assertEqual(pets[0].external_pet_id, "99")
        self.assertEqual(pets[0].external_org_id, "1")
        self.assertEqual(pets[0].species, "DOG")
        self.assertTrue(pets[0].photos)
