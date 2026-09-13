from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PlannerData(BaseModel):
    #The tags list must contain exactly three items.
    tags: list[str] = Field(
        ...,
        min_length=3,
        max_length=3
    )

    #Summary is a required string.
    summary: str

    #Check the length of every tag
    @field_validator("tags")
    @classmethod
    def check_tag_length(cls, v: list[str]) -> list[str]:
        #Go through every tag in the list.
        for tag in v:
            tag_length = len(tag)

            #Each tag must have between 3 and 30 characters.
            if tag_length < 3 or tag_length > 30:
                raise ValueError(
                    f"Tag '{tag}' has {tag_length} characters; "
                    "each tag must have between 3 and 30 characters."
                )

        #Return the tags if all of them passed validation
        return v

    #Check how many words are in the summary.
    @field_validator("summary")
    @classmethod
    def check_summary_words(cls, v: str) -> str:
        #split() separates the summary by spaces.
        #len() counts how many words are in the resulting list
        word_count = len(v.split())

        #Summary cannot contain more than 25 words.
        if word_count > 25:
            raise ValueError(
                f"Summary has {word_count} words; "
                "summary must contain no more than 25 words."
            )

        #Return the summary if it passed validation.
        return v