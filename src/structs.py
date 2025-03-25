from dataclasses import dataclass


@dataclass
class CommandValues:
    """
    Values as commanded from CoCT to outstation
    """

    def __init__(
        self,
        production_constraint_setpoint: float,
        gradient_ramp_up: int,
        gradient_ramp_down: int,
    ) -> None:
        self.production_constraint_setpoint = (
            production_constraint_setpoint  # 0 - master output index
        )

        self.gradient_ramp_up = gradient_ramp_up  # 1
        self.gradient_ramp_down = gradient_ramp_down  # 2

    @property
    def production_constraint_setpoint(self) -> float:
        return self._production_constraint_setpoint

    @production_constraint_setpoint.setter
    def production_constraint_setpoint(self, value) -> None:
        """sets production constraint and modifies flag appropriately"""
        if value < 0 or value > 100:
            raise ValueError(f"Attempt to set invalid production constraint. {value=}")

        self._production_constraint_setpoint = value

    @property
    def gradient_ramp_up(self) -> int:
        return self._gradient_ramp_up

    @gradient_ramp_up.setter
    def gradient_ramp_up(self, value) -> None:
        """sets gradient_ramp_up and modifies flag appropriately"""
        if value < 0 or value > 100:
            raise ValueError(f"Attempt to set invalid ramp up. {value=}")

        self._gradient_ramp_up = value

    @property
    def gradient_ramp_down(self) -> int:
        return self._gradient_ramp_down

    @gradient_ramp_down.setter
    def gradient_ramp_down(self, value) -> None:
        """sets gradient_ramp_down and modifies flag appropriately"""
        if value < 0 or value > 100:
            raise ValueError(f"Attempt to set invalid ramp down. {value=}")

        self._gradient_ramp_down = value

    def __iter__(self):
        members = (
            self.production_constraint_setpoint,
            self.gradient_ramp_up,
            self.gradient_ramp_down,
        )
        for member in members:
            yield member

    def asdict(self):
        d = {
            "production_constraint_setpoint": self.production_constraint_setpoint,
            "gradient_ramp_up": self.gradient_ramp_up,
            "gradient_ramp_down": self.gradient_ramp_down,
        }
        return d


if __name__ == "__main__":

    def test_setters():
        cmds = CommandValues(100, 5, 5)
        print(
            f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}"
        )

        cmds.production_constraint_setpoint = 90
        print(
            f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}"
        )

        cmds.gradient_ramp_down = 100
        print(
            f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}"
        )

        cmds.gradient_ramp_up = 100
        print(
            f"{cmds}, {cmds.flag_production_constraint}, {cmds.flag_gradient_constraint}"
        )

    test_setters()
