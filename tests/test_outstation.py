import unittest

from outstation import DNP3Outstation


class TestOutstation(unittest.TestCase):
    def setUp(self):
        self.defaultOutstation = DNP3Outstation()

    def test(self):
        pass


if __name__ == "__main__":
    unittest.main()