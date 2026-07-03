
import logging
# Mocking p4runtime_shell for portability
# In production: from p4runtime_shell.switch import SwitchConnection

class SketchManager:
    def __init__(self, switch_connection, register_name="MyIngress.sketch_register"):
        self.sw = switch_connection
        self.register_name = register_name
        self.size = 16384 # Must match P4 BLOOM_FILTER_SIZE

    def fetch_and_reset_sketch(self):
        """
        Reads the register array from the data plane and resets it to zero.
        Returns: A list of integers (0 or 1) representing the bloom filter.
        """
        try:
            # 1. Read Register entries
            # In P4Runtime, this involves creating a ReadRequest
            print(f"[SketchManager] Reading register: {self.register_name}")
            
            # SIMULATION: Generating mock data for the sake of the example
            # In a real burst, about 70-80% of bits might be set.
            import random
            mock_density = random.choice([0.1, 0.2, 0.8]) # 0.8 represents a burst
            sketch_data = [1 if random.random() < mock_density else 0 for _ in range(self.size)]
            
            # 2. Reset Register (Write 0s)
            # print(f"[SketchManager] Resetting register...")
            
            return sketch_data
        except Exception as e:
            logging.error(f"Error reading sketch: {e}")
            return []

    def calculate_density(self, sketch_data):
        """
        Calculates the ratio of set bits to total size.
        """
        if not sketch_data: return 0.0
        set_bits = sum(sketch_data)
        return set_bits / len(sketch_data)