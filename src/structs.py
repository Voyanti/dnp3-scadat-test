from dataclasses import dataclass, field

@dataclass
class Values:
    """
        Contains variables read for all relevant datapoints.
    """
    # W/Var
    plant_ac_power_generated: float = 1000                 # by Embedded Generation (EG) PLant
    grid_reactive_power: float = -50                       # at point of connection (POC) to CCT
    grid_exported_power: float = -300           # at POC

    # %
    production_constraint_setpoint: int = 0       # 0 - master output index
    gradient_ramp_up: int = 100      # 1
    gradient_ramp_down: int = 100    # 2

    # enable/disable
    flag_production_constraint: bool = True
    flag_gradient_constraint: bool = False    # VRAAG hoe word hierdie waardes bepaal/ geaffekteer
        

@dataclass
class CommandValues:
    """
        Contains command values for writeable datapoints.
    """
    def __init__(self, production_constraint_setpoint, gradient_ramp_up, gradient_ramp_down) -> None:
        self.production_constraint_setpoint: int = production_constraint_setpoint         # 0 - master output index
        self.gradient_ramp_up: int = gradient_ramp_up      # 1
        self.gradient_ramp_down: int = gradient_ramp_down    # 2
        
        # indicator flags: properties only

    @property
    def production_constraint_setpoint(self) -> int: return self._production_constraint_setpoint

    @production_constraint_setpoint.setter
    def production_constraint_setpoint(self, value) -> None:
        """ sets production constraint and modifies flag appropriately """
        if value < 0 or value > 100:
            raise ValueError(f"Attempt to set invalid production constraint. {value=}")
        
        self._production_constraint_setpoint = value


    @property
    def gradient_ramp_up(self) -> int: return self._gradient_ramp_up
    
    @gradient_ramp_up.setter
    def gradient_ramp_up(self, value) -> None:
        """ sets gradient_ramp_up and modifies flag appropriately """
        if value < 0 or value > 100:
            raise ValueError(f"Attempt to set invalid ramp up. {value=}")
        
        self._gradient_ramp_up = value


    @property
    def gradient_ramp_down(self) -> int: return self._gradient_ramp_down

    @gradient_ramp_down.setter
    def gradient_ramp_down(self, value) -> None:
        """ sets gradient_ramp_down and modifies flag appropriately """
        if value < 0 or value > 100:
            raise ValueError(f"Attempt to set invalid ramp down. {value=}")
        
        self._gradient_ramp_down = value


    @property
    def flag_production_constraint(self) -> bool:
        """ production constraint mode is disabled if 100. """
        return self.production_constraint_setpoint != 100 
    
    @property
    def flag_gradient_constraint(self) -> bool:
        """ gradient constraint mode is disabled if both ramp up and ramp down == 100. """
        return not (self.gradient_ramp_down==100 and self.gradient_ramp_up==100)




if __name__ == "__main__":
    def test_setters():
        cmds = CommandValues(
            100,
            5,
            5
        )
        print(f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}")
        assert(not cmds.flag_production_constraint)
        assert(cmds.flag_gradient_constraint)

        cmds.production_constraint_setpoint = 90
        print(f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}")
        assert(cmds.flag_production_constraint)
        assert(cmds.flag_gradient_constraint)

        cmds.gradient_ramp_down = 100
        print(f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}")
        assert(cmds.flag_production_constraint)
        assert(cmds.flag_gradient_constraint)

        cmds.gradient_ramp_up = 100
        print(f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}")
        assert(cmds.flag_production_constraint)
        assert(not cmds.flag_gradient_constraint)

    test_setters()
