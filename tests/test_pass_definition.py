import unittest

from rulecraft.schemas import VerifierResult, pass_definition


class PassDefinitionTests(unittest.TestCase):
    def test_pass_definition_ok(self) -> None:
        verifier = VerifierResult(
            schema_version="0.5.15",
            verifier_id="test",
            verdict="PASS",
            outcome="OK",
        )
        self.assertTrue(pass_definition(verifier))

    def test_pass_definition_fail_outcome(self) -> None:
        verifier = VerifierResult(
            schema_version="0.5.15",
            verifier_id="test",
            verdict="PASS",
            outcome="FAIL",
        )
        self.assertFalse(pass_definition(verifier))


if __name__ == "__main__":
    unittest.main()
