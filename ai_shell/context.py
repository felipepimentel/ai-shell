class ExecutionContext:
    def __init__(self, simulation_mode=False, verbose_mode=False):
        self.simulation_mode = simulation_mode
        self.verbose_mode = verbose_mode

    def toggle_simulation_mode(self):
        self.simulation_mode = not self.simulation_mode
