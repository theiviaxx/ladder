import unittest

from models import Ladder


class LadderTestCase(unittest.TestCase):
    def setUp(self):
        self.ladder = Ladder.objects.create(name='Ladder1')