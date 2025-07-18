from pydantic import BaseModel, Field


class PhotoOption(BaseModel):
    """Represents a photo option with its metadata and source URLs."""

    url: str = Field(description="Link to the photo")
    alt: str = Field(description="Alternative text for the photo")
    src: dict[str, str] = Field(
        description="Link to the photo with different sizes and qualities"
    )


class Media(BaseModel):
    """Visual memory aid with explanation and learning tips in the source language."""

    url: str = Field(
        description="Link to the website where the visual media can be found"
    )
    alt: str = Field(
        description="Alternative text for the visual media in the source language"
    )
    src: dict[str, str] = Field(
        description="Link to the photo or video with different sizes and qualities"
    )
    explanation: str = Field(
        ...,
        min_length=20,
        description="Detailed explanation of why this visual is memorable for learning the word in the source language",
    )
    memory_tip: str = Field(
        ...,
        min_length=10,
        description="Specific tip for using this visual to remember the word in the source language",
    )


class SearchQueryResult(BaseModel):
    search_query: list[str] = Field(
        description="English search query to find the most relevant photos in Pexels. Each entry should be 1-2 words maximum, with 2-3 total entries.",
        min_length=1,
        max_length=3,
    )
