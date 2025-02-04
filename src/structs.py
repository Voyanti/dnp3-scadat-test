from dataclasses import dataclass

@dataclass
class Values:
    """
        Contains variables read for all relevant datapoints.
    """
    # W/Var
    total_power_generated: float = 0                # by Embedded Generation (EG) PLant
    reactive_power: float = 0                       # at point of connection (POC) to CCT
    exported_or_imported_power: float = 0           # at POC

    # %
    production_constraint_setpoint: int = 100       # 0 - master output index
    power_gradient_constraint_ramp_up: int = 5      # 1
    power_gradient_constraint_ramp_down: int = 5    # 2

    # enable/disable
    production_constraint_mode: bool = True
    power_gradient_constraint_mode: bool = False    # VRAAG hoe word hierdie waardes bepaal/ geaffekteer

@dataclass
class CommandValues:
    """
        Contains command values for writeable datapoints.
    """
    production_constraint_setpoint: int         # 0 - master output index
    power_gradient_constraint_ramp_up: int      # 1
    power_gradient_constraint_ramp_down: int    # 2