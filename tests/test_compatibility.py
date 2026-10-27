import unittest

from flpswap.compatibility import assess_compatibility


class CompatibilityAssessmentTests(unittest.TestCase):
    def test_same_version_is_not_called_converted(self):
        result = assess_compatibility("21.2.3.4004", "21.2.3")
        self.assertEqual(result.relation, "same_version")
        self.assertFalse(result.conversion_supported)
        self.assertEqual(result.status, "assessment_only")

    def test_newer_source_warns_about_downgrade(self):
        result = assess_compatibility("26.1.7.5653", "21.3.6")
        self.assertEqual(result.relation, "source_newer_than_target")
        self.assertTrue(any("más reciente" in warning for warning in result.warnings))

    def test_unknown_source_does_not_guess(self):
        result = assess_compatibility(None, "21.3.6")
        self.assertEqual(result.relation, "unknown")

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            assess_compatibility("26.1.7", "FL Studio 21")


if __name__ == "__main__":
    unittest.main()
