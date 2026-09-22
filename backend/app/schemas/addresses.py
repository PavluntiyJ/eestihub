from typing import Literal

from pydantic import BaseModel, Field


MatchQuality = Literal["exact", "partial", "unknown"]


class AddressCandidate(BaseModel):
    # ads_oid is opaque: EE/ME prefixes observed, never validated.
    id: str
    label: str
    short_label: str
    longitude: float
    latitude: float
    # No district inference until the M09 geometry work; always null.
    district_id: None = None
    quality: MatchQuality


class AddressAttribution(BaseModel):
    provider: Literal["maa_ja_ruumiamet"]
    label: str
    source_url: str


class AddressSearchResponse(BaseModel):
    query: str
    candidates: list[AddressCandidate] = Field(default_factory=list)
    attribution: AddressAttribution
