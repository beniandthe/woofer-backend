from django.test import SimpleTestCase
from adoption.services.pet_enrichment_service import PetEnrichmentService

class PetEnrichmentServiceTests(SimpleTestCase):
    def test_returns_none_on_empty(self):
        self.assertIsNone(PetEnrichmentService.generate_fun_neutral_summary(None))
        self.assertIsNone(PetEnrichmentService.generate_fun_neutral_summary("   "))

    def test_fun_but_neutral(self):
        raw = "Sweet, friendly, playful girl. Great with kids. Loves walks."
        out = PetEnrichmentService.generate_fun_neutral_summary(raw)
        self.assertIn("sweet", out.lower())
        self.assertIn("friendly", out.lower())
        # neutral, should not contain hype words we didn't provide
        self.assertNotIn("perfect", out.lower())
        self.assertTrue(len(out) <= PetEnrichmentService.MAX_LEN)
