from django.test import SimpleTestCase

from adoption.services.ranking_service import RankingService


class RankingBoostedTests(SimpleTestCase):
    def test_is_boosted_true_when_reasons_present(self):
        self.assertTrue(RankingService.is_boosted(["LONG_STAY_BOOST"]))

    def test_is_boosted_false_when_reasons_empty(self):
        self.assertFalse(RankingService.is_boosted([]))
