from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
import numpy as np
import pandas as pd # Still useful for reference data

# --- Data Definitions (More Detailed) ---

class Contaminant:
    """Represents a type of water contaminant."""
    def __init__(self, name, initial_level, unit="units"):
        self.name = name
        self.initial_level = initial_level
        self.current_level = initial_level
        self.unit = unit

    def reduce(self, percentage):
        """Reduces the contaminant level by a given percentage."""
        reduction_factor = 1 - (percentage / 100.0)
        self.current_level *= reduction_factor
        if self.current_level < 0.01: # Cap at near zero for display
            self.current_level = 0.0
        return percentage * self.initial_level / 100.0 # Return amount reduced

class WaterQuality:
    """Manages a collection of contaminants."""
    def __init__(self, description=""):
        self.description = description
        self.contaminants = {}

    def add_contaminant(self, contaminant: Contaminant):
        self.contaminants[contaminant.name] = contaminant

    def get_contaminant_level(self, name):
        return self.contaminants.get(name, Contaminant(name, 0)).current_level

    def get_all_levels(self):
        return {name: cont.current_level for name, cont in self.contaminants.items()}

    def apply_removal(self, removal_efficiencies: dict):
        """Applies removal efficiencies to current contaminant levels.
           removal_efficiencies: {contaminant_name: percentage_removal}
        """
        for name, efficiency in removal_efficiencies.items():
            if name in self.contaminants:
                self.contaminants[name].reduce(efficiency)

    def copy(self):
        """Creates a deep copy of the WaterQuality object."""
        new_wq = WaterQuality(self.description + " (Copy)")
        for name, cont in self.contaminants.items():
            new_cont = Contaminant(cont.name, cont.initial_level, cont.unit)
            new_cont.current_level = cont.current_level
            new_wq.add_contaminant(new_cont)
        return new_wq

class FiltrationMaterial:
    """Defines properties and effectiveness of a filter material."""
    def __init__(self, name, description, efficiency: dict, effect_on_flow: float, draw_moisture=False):
        self.name = name
        self.description = description
        # efficiency: {contaminant_name: removal_percentage}
        self.efficiency = efficiency
        # effect_on_flow: 1.0 for easy flow, <1.0 restricts, >1.0 enhances
        self.effect_on_flow = effect_on_flow
        # draw_moisture: Can this material wick water from the ground?
        self.draw_moisture = draw_moisture

# --- Filtration Material Data (Based on your request) ---
# Note: These percentages are illustrative and can be fine-tuned.
charcoal_filter = FiltrationMaterial(
    "Charcoal (Activated Carbon)",
    "Excellent for adsorbing organic chemicals, odors, and chlorine.",
    efficiency={
        "Organic Chemicals": 80, # High
        "Chlorine": 95,
        "Heavy Metals": 20, # Moderate, depends on type
        "Suspended Solids": 10, # Minimal for larger particles
        "Bacteria": 5 # Not its primary function, but some large ones might get trapped
    },
    effect_on_flow=0.7 # Moderately restrictive flow
)

gravel_filter = FiltrationMaterial(
    "Gravel",
    "Removes large suspended solids and provides drainage.",
    efficiency={
        "Suspended Solids": 70, # High for larger ones
        "Organic Chemicals": 0,
        "Bacteria": 0 # Does not remove
    },
    effect_on_flow=1.2 # Enhances flow/drainage
)

sand_filter = FiltrationMaterial(
    "Sand (Fine)",
    "Removes finer suspended solids and allows for capillary action.",
    efficiency={
        "Suspended Solids": 85, # Very good for finer particles
        "Organic Chemicals": 5, # Very minor adsorption
        "Bacteria": 10 # Some trapping, but not full removal
    },
    effect_on_flow=0.8, # More restrictive than gravel
    draw_moisture=True # Key for drawing water from ground
)

# Reference for distillation
distillation_process = FiltrationMaterial(
    "Distillation (Evaporation/Condensation)",
    "Removes virtually all non-volatile impurities.",
    efficiency={
        "Suspended Solids": 99.9,
        "Organic Chemicals": 95, # Volatile organics can co-distill, so not 100%
        "Heavy Metals": 99.5,
        "Salts": 99.9,
        "Bacteria": 99.9,
        "Viruses": 99.9,
        "Protozoa": 99.9,
        "Chlorine": 90
    },
    effect_on_flow=1.0 # N/A for flow in this context, it's a phase change
)


class SolarDistillationSimulator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.temperature = 40  # Initial temperature (Celsius)
        self.time_step = 0
        self.sim_running = False

        # --- Water Quality States ---
        self.raw_water_quality = self._initialize_bad_water()
        self.filtered_water_quality = WaterQuality("Pre-Distillation Filtered Water")
        self.distilled_water_quality = WaterQuality("Final Distilled Water")

        # --- Filtration Layers in the Still (order matters for physical filters) ---
        self.filtration_layers = [
            gravel_filter,
            sand_filter, # Sand on top of gravel in some designs, or below if drawing from ground
            charcoal_filter
        ]
        self.ground_moisture_level = 100 # Simulating initial ground moisture content (arbitrary units)

        # --- UI Elements ---
        self.add_widget(Label(text="--- Solar Distillation Simulation ---"))
        self.clarity_label = Label(text="Clarity: Calculating...")
        self.add_widget(self.clarity_label)

        self.status_label = Label(text="Starting simulation...\n")
        self.add_widget(self.status_label)

        self.contaminant_display_label = Label(text="Initial Contaminants:")
        self.add_widget(self.contaminant_display_label)

    def _initialize_bad_water(self):
        """Sets up the initial 'bad' water quality."""
        wq = WaterQuality("Raw Water")
        wq.add_contaminant(Contaminant("Suspended Solids", 500, "mg/L")) # Cloudy
        wq.add_contaminant(Contaminant("Organic Chemicals", 100, "ug/L")) # Bad taste/smell
        wq.add_contaminant(Contaminant("Heavy Metals", 50, "ug/L"))
        wq.add_contaminant(Contaminant("Salts", 1000, "mg/L"))
        wq.add_contaminant(Contaminant("Bacteria", 10000, "CFU/mL")) # High bacterial count
        wq.add_contaminant(Contaminant("Chlorine", 1.5, "mg/L"))
        return wq

    def start_simulation(self):
        self.time_step = 0
        self.sim_running = True
        self.raw_water_quality = self._initialize_bad_water() # Reset for restart
        self.filtered_water_quality = WaterQuality("Pre-Distillation Filtered Water") # Reset
        self.distilled_water_quality = WaterQuality("Final Distilled Water") # Reset

        self._update_contaminant_display("Initial Water Quality", self.raw_water_quality)
        self.status_label.text = "Simulating water purification...\n"
        self.clarity_label.text = "Clarity: 0.00 (Dirty)"
        Clock.schedule_interval(self.simulate_step, 0.5) # Faster for demo

    def _update_contaminant_display(self, title, water_quality_obj):
        """Updates the label showing contaminant levels."""
        display_text = f"{title}:\n"
        for name, level in water_quality_obj.get_all_levels().items():
            cont = water_quality_obj.contaminants[name]
            display_text += f"  {name}: {level:.2f} {cont.unit}\n"
        self.contaminant_display_label.text = display_text

    def calculate_clarity(self):
        """Calculates clarity based on residual suspended solids and organics."""
        # Lower levels of these mean higher clarity
        max_solids = self.raw_water_quality.get_contaminant_level("Suspended Solids")
        max_organics = self.raw_water_quality.get_contaminant_level("Organic Chemicals")

        current_solids = self.distilled_water_quality.get_contaminant_level("Suspended Solids")
        current_organics = self.distilled_water_quality.get_contaminant_level("Organic Chemicals")

        # Avoid division by zero if initial levels were 0
        solids_clarity = 1.0 - (current_solids / max_solids if max_solids > 0 else 0)
        organics_clarity = 1.0 - (current_organics / max_organics if max_organics > 0 else 0)

        # Simple weighted average for overall clarity
        clarity = (solids_clarity * 0.6) + (organics_clarity * 0.4)
        return np.clip(clarity, 0.0, 1.0) # Ensure it's between 0 and 1

    def simulate_step(self, dt):
        if not self.sim_running:
            return False

        self.time_step += 1
        step_message = f"--- Step: {self.time_step} ---\n"
        step_message += f"Current Temperature: {self.temperature:.1f}°C\n"

        # 1. Simulate Capillary Action (Soil/Sand)
        capillary_draw_rate = 0.0 # How much new 'bad water' is introduced per step
        for material in self.filtration_layers:
            if material.draw_moisture and self.ground_moisture_level > 0:
                # Simulate drawing up new raw water from the ground based on material's flow
                # This will increase the contaminant levels of the 'raw' water slightly
                draw_amount = 0.05 * material.effect_on_flow # Adjust for realism
                if self.ground_moisture_level - draw_amount < 0:
                    draw_amount = self.ground_moisture_level
                self.ground_moisture_level -= draw_amount
                capillary_draw_rate += draw_amount # Accumulate how much was drawn

                # If new water is drawn, re-introduce a small portion of initial contaminants
                # This makes the simulation run longer before reaching 'clear' if ground moisture is present
                for name, initial_cont in self.raw_water_quality.contaminants.items():
                    # For simplicity, let's say 1% of the initial level is added back if water is drawn
                    # This simulates continuous contamination from the ground if not completely sealed
                    re_contamination_amount = initial_cont.initial_level * 0.01 * (draw_amount / 0.05)
                    self.raw_water_quality.contaminants[name].current_level = min(
                        initial_cont.initial_level, # Don't exceed initial bad water level
                        self.raw_water_quality.contaminants[name].current_level + re_contamination_amount
                    )
                step_message += f"Capillary action drawing water from ground ({draw_amount:.2f} units). Ground moisture: {self.ground_moisture_level:.1f}\n"

        # Make a copy for physical filtration, so original raw water remains for capillary re-introduction
        self.filtered_water_quality = self.raw_water_quality.copy()
        step_message += "Applying Physical Filtration (Gravel, Sand, Charcoal):\n"
        for material in self.filtration_layers:
            self.filtered_water_quality.apply_removal(material.efficiency)
            step_message += f"  - Applied {material.name} filter. Flow effect: {material.effect_on_flow:.1f}\n"

        # 2. Simulate Evaporation & Condensation (Distillation)
        # Distillation is highly effective
        evaporation_eff = np.clip(0.1 + (self.temperature - 25) * 0.02, 0.01, 1.0)
        condensation_eff = np.clip(0.6 + (self.temperature - 25) * 0.01, 0.01, 1.0)

        # The distillation process acts on the already filtered water
        self.distilled_water_quality = self.filtered_water_quality.copy()
        distillation_removal_dict = {
            name: dist_eff * (evaporation_eff + condensation_eff) / 2 * 100 # Adjust percentage by process effectiveness
            for name, dist_eff in distillation_process.efficiency.items()
        }
        self.distilled_water_quality.apply_removal(distillation_removal_dict)
        step_message += f"Distillation (Evaporation: {evaporation_eff:.2f}, Condensation: {condensation_eff:.2f}) applied.\n"

        # Update clarity based on final distilled water quality
        current_clarity = self.calculate_clarity()
        clarity_status = ""
        if current_clarity < 0.3:
            clarity_status = "(Very Dirty)"
        elif current_clarity < 0.6:
            clarity_status = "(Cloudy)"
        elif current_clarity < 0.9:
            clarity_status = "(Clearing Up)"
        else:
            clarity_status = "(Clear!)"

        self.clarity_label.text = f"Clarity: {current_clarity:.2f} {clarity_status}"
        self.status_label.text = step_message

        # Update contaminant display
        self._update_contaminant_display("Distilled Water Quality", self.distilled_water_quality)

        # Check for completion
        # Define 'clear' as most contaminants being very low
        is_clear = all(self.distilled_water_quality.get_contaminant_level(c_name) < (c_cont.initial_level * 0.01)
                       for c_name, c_cont in self.raw_water_quality.contaminants.items())

        if is_clear and current_clarity >= 0.95:
            self.status_label.text += "\nWater is now clear and pure! Simulation complete."
            self.sim_running = False
            Clock.unschedule(self.simulate_step) # Explicitly unschedule
            return False

        return True  # Continue scheduling

class SolarDistillationApp(App):
    def build(self):
        root = SolarDistillationSimulator()
        # Start after 1 sec to allow UI to build
        Clock.schedule_once(lambda dt: root.start_simulation(), 1)
        return root

if __name__ == "__main__":
    print("--- Filtration Materials Data (for reference) ---")
    print(charcoal_filter.name)
    print(f"  Description: {charcoal_filter.description}")
    print(f"  Efficiencies: {charcoal_filter.efficiency}")
    print(f"  Flow Effect: {charcoal_filter.effect_on_flow}\n")

    print(gravel_filter.name)
    print(f"  Description: {gravel_filter.description}")
    print(f"  Efficiencies: {gravel_filter.efficiency}")
    print(f"  Flow Effect: {gravel_filter.effect_on_flow}\n")

    print(sand_filter.name)
    print(f"  Description: {sand_filter.description}")
    print(f"  Efficiencies: {sand_filter.efficiency}")
    print(f"  Flow Effect: {sand_filter.effect_on_flow}")
    print(f"  Draw Moisture (Capillary): {sand_filter.draw_moisture}\n")

    print("--------------------------------------------------\n")

    SolarDistillationApp().run()
