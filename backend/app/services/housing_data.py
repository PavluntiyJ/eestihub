from typing import NamedTuple


class DistrictRentData(NamedTuple):
    name: str
    avg_rent_1room: int
    avg_rent_2room: int
    avg_rent_3room: int
    avg_utilities: int
    lat: float
    lon: float


# Mock Tallinn district rent data for the MVP, prepared on 2026-07-09.
CITY = "Tallinn"
UPDATED_AT = "2026-07-01"
DISTRICT_RENTS: tuple[DistrictRentData, ...] = (
    DistrictRentData("Kesklinn", 650, 900, 1250, 210, 59.437, 24.753),
    DistrictRentData("Põhja-Tallinn", 560, 780, 1050, 190, 59.453, 24.703),
    DistrictRentData("Kristiine", 520, 720, 960, 185, 59.424, 24.716),
    DistrictRentData("Mustamäe", 470, 650, 850, 175, 59.399, 24.672),
    DistrictRentData("Lasnamäe", 430, 590, 780, 170, 59.440, 24.862),
    DistrictRentData("Haabersti", 500, 690, 920, 180, 59.426, 24.646),
    DistrictRentData("Nõmme", 540, 740, 1020, 195, 59.386, 24.690),
    DistrictRentData("Pirita", 590, 820, 1150, 205, 59.469, 24.833),
)
