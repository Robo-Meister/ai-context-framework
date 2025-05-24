from interfaces.filter_strategy import FilterStrategy


class VectorCalculator:
    def __init__(self, encoder, filter_strategy: FilterStrategy = None):
        self.encoder = encoder
        self.filter = filter_strategy

    def calculate(self, context_input):
        vector = self.encoder.encode(context_input)
        if self.filter:
            vector = self.filter.apply(vector)
        return vector
