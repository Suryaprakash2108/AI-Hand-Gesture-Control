import unittest
import math
import os
import sys

# Add project root directory to the python path to ensure import resolution
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from smoothing import EMAFilter
from gesture_engine import GestureEngine
from main import verify_system_requirements

class TestSmoothingFilter(unittest.TestCase):
    def test_ema_initialization(self):
        """Verify EMA filter initializes with default and custom alpha parameters."""
        filter_default = EMAFilter()
        self.assertEqual(filter_default.alpha, 0.25)
        
        filter_custom = EMAFilter(alpha=0.5)
        self.assertEqual(filter_custom.alpha, 0.5)

    def test_ema_first_update(self):
        """The first update of EMA filter should return the exact coordinates input (no history)."""
        ema = EMAFilter(alpha=0.2)
        x, y = ema.update(100, 200)
        self.assertEqual((x, y), (100, 200))
        self.assertEqual(ema.prev_x, 100)
        self.assertEqual(ema.prev_y, 200)

    def test_ema_smoothing_convergence(self):
        """Verify the exponential moving average mathematical formula application."""
        alpha = 0.5
        ema = EMAFilter(alpha=alpha)
        
        # First point sets the initial state
        ema.update(100, 100)
        
        # Second point: S_t = 0.5 * 200 + (1 - 0.5) * 100 = 150
        x, y = ema.update(200, 200)
        self.assertEqual((x, y), (150, 150))
        
        # Third point: S_t = 0.5 * 100 + 0.5 * 150 = 125
        x, y = ema.update(100, 100)
        self.assertEqual((x, y), (125, 125))

    def test_ema_reset(self):
        """Verify resetting the filter clears the memory cache."""
        ema = EMAFilter(alpha=0.1)
        ema.update(100, 100)
        ema.update(200, 200)
        
        ema.reset()
        self.assertIsNone(ema.prev_x)
        self.assertIsNone(ema.prev_y)
        
        # After reset, next coordinate should act as a first point
        x, y = ema.update(300, 400)
        self.assertEqual((x, y), (300, 400))

    def test_ema_set_alpha_boundary_limits(self):
        """Ensure alpha value is always bounded within safe ranges [0.01, 1.0]."""
        ema = EMAFilter(alpha=0.2)
        
        # Upper bound overflow
        ema.set_alpha(1.5)
        self.assertEqual(ema.alpha, 1.0)
        
        # Lower bound underflow
        ema.set_alpha(-0.5)
        self.assertEqual(ema.alpha, 0.01)
        
        # Inside normal bounds
        ema.set_alpha(0.4)
        self.assertEqual(ema.alpha, 0.4)


class TestGestureEngineMath(unittest.TestCase):
    def setUp(self):
        # Instantiate GestureEngine with a dummy/no callback
        self.engine = GestureEngine()

    def test_distance_calculation(self):
        """Verify Euclidean 2D distance calculations."""
        p1 = (0, 0)
        p2 = (3, 4)  # 3-4-5 triangle rule
        dist = self.engine._calculate_distance(p1, p2)
        self.assertAlmostEqual(dist, 5.0)
        
        p3 = (10, 10)
        p4 = (10, 10)
        self.assertEqual(self.engine._calculate_distance(p3, p4), 0.0)

    def test_settings_updates(self):
        """Verify thread-safe updates to engine metrics."""
        self.engine.update_settings(pointer_speed=2.5, click_threshold=35.0)
        
        self.assertEqual(self.engine.pointer_speed, 2.5)
        self.assertEqual(self.engine.click_threshold, 35.0)


class TestSystemChecks(unittest.TestCase):
    def test_requirements_validator(self):
        """Verify system requirements pass under standard execution environment."""
        # This will verify requirements under the current running virtual env
        self.assertTrue(verify_system_requirements())


if __name__ == "__main__":
    unittest.main()
