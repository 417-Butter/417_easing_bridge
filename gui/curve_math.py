class BezierSegment:
    def __init__(self, p0_x, p0_y, p1_x, p1_y, p2_x, p2_y, p3_x, p3_y):
        self.p0_x = p0_x
        self.p0_y = p0_y
        self.p1_x = max(p0_x, min(p3_x, p1_x))
        self.p1_y = p1_y
        self.p2_x = max(p0_x, min(p3_x, p2_x))
        self.p2_y = p2_y
        self.p3_x = p3_x
        self.p3_y = p3_y

    def sample_curve_x(self, t):
        return ((1-t)**3)*self.p0_x + 3*((1-t)**2)*t*self.p1_x + 3*(1-t)*(t**2)*self.p2_x + (t**3)*self.p3_x

    def sample_curve_y(self, t):
        return ((1-t)**3)*self.p0_y + 3*((1-t)**2)*t*self.p1_y + 3*(1-t)*(t**2)*self.p2_y + (t**3)*self.p3_y
        
    def sample_curve_derivative_x(self, t):
        return 3*((1-t)**2)*(self.p1_x - self.p0_x) + 6*(1-t)*t*(self.p2_x - self.p1_x) + 3*(t**2)*(self.p3_x - self.p2_x)

    def solve_curve_x(self, x, epsilon=1e-6):
        t2 = (x - self.p0_x) / (self.p3_x - self.p0_x + 1e-8)  # initial guess
        for i in range(8):
            x2 = self.sample_curve_x(t2) - x
            if abs(x2) < epsilon: return t2
            d2 = self.sample_curve_derivative_x(t2)
            if abs(d2) < 1e-6: break
            t2 = t2 - x2 / d2
            
        t0, t1 = 0.0, 1.0
        t2 = (x - self.p0_x) / (self.p3_x - self.p0_x + 1e-8)
        while t0 < t1:
            x2 = self.sample_curve_x(t2)
            if abs(x2 - x) < epsilon: return t2
            if x > x2: t0 = t2
            else: t1 = t2
            t2 = (t1 - t0) * 0.5 + t0
        return t2

    def get_y_for_x(self, x):
        t = self.solve_curve_x(x)
        return self.sample_curve_y(t)


class CompositeBezier:
    def __init__(self, segments=None):
        self.segments = segments if segments else []
        
    def get_y_for_x(self, x):
        if not self.segments:
            return x
        if x <= self.segments[0].p0_x:
            return self.segments[0].p0_y
        if x >= self.segments[-1].p3_x:
            return self.segments[-1].p3_y
            
        for seg in self.segments:
            if seg.p0_x <= x <= seg.p3_x:
                return seg.get_y_for_x(x)
        return self.segments[-1].p3_y


def generate_easing_table(composite_curve, frame_count):
    if frame_count <= 0:
        return [0.0]
    table = []
    for i in range(frame_count + 1):
        x = i / frame_count
        y = composite_curve.get_y_for_x(x)
        table.append(y)
    return table
