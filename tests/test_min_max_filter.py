import unittest
import numpy as np

from caiengine.core.filters.min_max_filter import MinMaxFilter


class TestMinMaxFilter(unittest.TestCase):
    def test_scalar(self):
        filt = MinMaxFilter(0, 10)
        self.assertEqual(filt.apply(5), 5)
        self.assertEqual(filt.apply(-1), 0)
        self.assertEqual(filt.apply(15), 10)

    def test_list(self):
        filt = MinMaxFilter(-1, 1)
        self.assertEqual(filt.apply([2, -2, 0]), [1, -1, 0])

    def test_array(self):
        filt = MinMaxFilter(0, 1)
        arr = np.array([-0.5, 0.5, 1.5])
        res = filt.apply(arr)
        np.testing.assert_array_equal(res, np.array([0.0, 0.5, 1.0]))


if __name__ == "__main__":
    unittest.main()
