class EMAFilter:
    """
    Exponential Moving Average (EMA) Filter for smoothing coordinates
    to prevent jittery mouse cursor movements.
    """
    def __init__(self, alpha=0.25):
        """
        Initialize the filter with a smoothing factor (alpha).
        alpha: float between 0.0 and 1.0.
               - Lower values = smoother cursor, but slight latency.
               - Higher values = more responsive cursor, but more jitter.
        """
        self.alpha = alpha
        self.prev_x = None
        self.prev_y = None

    def update(self, x, y):
        """
        Apply EMA filter to current x, y coordinates and return smoothed values.
        """
        if self.prev_x is None or self.prev_y is None:
            self.prev_x = x
            self.prev_y = y
            return int(x), int(y)

        # EMA formula: S_t = alpha * Y_t + (1 - alpha) * S_{t-1}
        smoothed_x = self.alpha * x + (1 - self.alpha) * self.prev_x
        smoothed_y = self.alpha * y + (1 - self.alpha) * self.prev_y

        self.prev_x = smoothed_x
        self.prev_y = smoothed_y

        return int(smoothed_x), int(smoothed_y)

    def reset(self):
        """
        Reset the filter state.
        """
        self.prev_x = None
        self.prev_y = None

    def set_alpha(self, alpha):
        """
        Dynamically adjust the smoothing factor.
        """
        self.alpha = max(0.01, min(1.0, alpha))
