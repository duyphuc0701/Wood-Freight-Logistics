from enum import Enum, auto


class EngineState(Enum):
    ENGINE_OFF = auto()
    ENGINE_ON_STATIONARY = auto()
    ENGINE_MOVING = auto()


def get_state(power_on: bool, speed: float) -> EngineState:
    if not power_on:
        return EngineState.ENGINE_OFF
    elif speed == 0:
        return EngineState.ENGINE_ON_STATIONARY
    else:
        return EngineState.ENGINE_MOVING
