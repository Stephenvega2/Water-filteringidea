from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
import numpy as np
import pandas as pd

# Filtration materials data (for reference)
filtration_materials = pd.DataFrame({
    "Material": ["Charcoal", "Gravel", "Magnet"],
    "Porosity": ["High", "Moderate", "None"],
    "Adsorption": ["Strong (traps toxins)", "Minimal", "Selective for ferromagnetic metals"],
    "Drainage": ["Moderate", "Excellent", "Not applicable"],
    "Particle Composition": ["Carbon-rich", "Coarse and fine particles", "Metallic (for attraction)"]
})

class SolarDistillationSimulator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.temperature = 40  # Initial temperature (Celsius)
        self.clarity = 0.0     # 0.0 = dirty, 1.0 = fully clear
        self.time_step = 0
        self.sim_running = False

        # Clarity result label (shown above the slider)
        self.clarity_label = Label(text="Clarity: 0.00 (Dirty)")
        self.add_widget(self.clarity_label)

        # Status label for progress messages
        self.status_label = Label(text="Starting simulation...\n")
        self.add_widget(self.status_label)

    def start_simulation(self):
        self.clarity = 0.0
        self.time_step = 0
        self.sim_running = True
        self.status_label.text = "Simulating water purification...\n"
        self.clarity_label.text = "Clarity: 0.00 (Dirty)"
        Clock.schedule_interval(self.simulate_step, 1.0)  # 1 second per step

    def simulate_step(self, dt):
        if not self.sim_running:
            return False

        # Simulate increases in clarity due to evaporation, condensation, and filtration
        evaporation = np.clip(0.1 + (self.temperature - 25) * 0.02, 0, 1)
        condensation = np.clip(0.6 + (self.temperature - 25) * 0.01, 0, 1)
        magnetic_eff = np.clip(0.5 + (self.temperature - 25) * 0.015, 0, 1)

        # Each step, clarity increases by a function of process effectiveness
        progress = (evaporation * 0.4) + (condensation * 0.4) + (magnetic_eff * 0.2)
        self.clarity = min(1.0, self.clarity + progress * 0.06)  # Adjust rate for realism

        self.time_step += 1
        # Update clarity label above the bar
        if self.clarity < 1.0:
            self.clarity_label.text = f"Clarity: {self.clarity:.2f} (Filtering)"
        else:
            self.clarity_label.text = f"Clarity: {self.clarity:.2f} (Clear!)"

        self.status_label.text = (
            f"Step: {self.time_step}\n"
            f"Evaporation: {evaporation:.2f}, Condensation: {condensation:.2f}, Magnetic: {magnetic_eff:.2f}\n"
        )

        if self.clarity >= 1.0:
            self.status_label.text += "\nWater is now clear! Simulation complete."
            self.sim_running = False
            return False  # Stops the scheduled Clock

        return True  # Continue scheduling

class SolarDistillationApp(App):
    def build(self):
        root = SolarDistillationSimulator()
        Clock.schedule_once(lambda dt: root.start_simulation(), 1)  # Start after 1 sec
        return root

if __name__ == "__main__":
    print("Filtration Materials Data:\n", filtration_materials)
    SolarDistillationApp().run()
