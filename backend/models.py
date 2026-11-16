from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DriverEdit(StrictModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    aggression: int | None = Field(default=None, ge=0, le=100)
    marketability: int | None = Field(default=None, ge=0, le=100)
    growth: int | None = Field(default=None, ge=0, le=100)
    stats: dict[int, int] = Field(default_factory=dict)


class ContractEdit(StrictModel):
    salary: int = Field(ge=0, le=1000000000)
    end_season: int = Field(ge=2022, le=2100)
    race_bonus: int = Field(ge=0, le=100000000)


class TeamEdit(StrictModel):
    balance: int = Field(ge=-1000000000, le=10000000000)


class CalendarEdit(StrictModel):
    weather: Literal[1, 2, 4, 8, 16, 32]
    temperature: float = Field(ge=-10, le=65)


class PartEdit(StrictModel):
    value: float = Field(ge=0, le=1000)


class ExpertiseEdit(StrictModel):
    expertise: float = Field(ge=0, le=1000)
    next_season: float = Field(ge=0, le=1000)


class TransferEdit(StrictModel):
    driver_id: int = Field(gt=0)
    team_id: int = Field(gt=0)
    seat: Literal[1, 2]
    timing: Literal["now", "next"] = "now"
    displaced: Literal["release", "swap", "reserve"] = "release"
    salary: int = Field(ge=0, le=1000000000)
    end_season: int = Field(ge=2022, le=2100)
    expected_outgoing: int | None = None


class AcademyEdit(StrictModel):
    driver_id: int = Field(gt=0)
    salary: int = Field(ge=0, le=1000000000)
    end_season: int = Field(ge=2022, le=2100)
    keep_feeder_seat: bool = True
    timing: Literal["now", "next"] = "now"


class EngineEdit(StrictModel):
    name: str = Field(min_length=1, max_length=60, pattern=r".*\S.*")
    power: float = Field(ge=80, le=100)
    fuel: float = Field(ge=50, le=100)
    durability: float = Field(ge=60, le=80)
    ers: float = Field(ge=50, le=70)
    gearbox: float = Field(ge=50, le=70)


class EngineCreate(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    base_engine: int = Field(gt=0)


class EngineAllocation(StrictModel):
    engine_id: int = Field(gt=0)


class FittedStat(StrictModel):
    design_id: int = Field(gt=0)
    stat_id: int = Field(ge=0, le=15)
    value: float


class FittedEdit(StrictModel):
    units: Literal["raw", "converted"] = "converted"
    stats: list[FittedStat] = Field(min_length=1, max_length=60)
