class LifecycleCalculator:
    """核心逻辑层：处理复杂的交通设施寿命预测"""

    @staticmethod
    def calculate_reliability(usage_time, intensity, environment_factor):
        # 假设的核心数学算法
        # Reliability = e^(-(t/alpha)^beta)
        score = (usage_time * intensity) / (1 + environment_factor)
        return max(0, 100 - score)