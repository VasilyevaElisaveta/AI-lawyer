from pydantic import BaseModel, Field, model_validator
from string import punctuation, ascii_uppercase, digits


class RegistrationRequestModel(BaseModel):

    model_config = {"extra": "forbid"}

    username: str
    password: str = Field(min_length=8)
    data_processing_policy_accepted: bool

    @model_validator(mode="after")
    def validate_password(self):
        has_digits = False
        has_upper_letters = False
        has_special_characters = False

        unique_letters = set(self.password)

        for letter in unique_letters:
            if letter in digits:
                has_digits = True
            elif letter in ascii_uppercase:
                has_upper_letters = True
            elif letter in punctuation:
                has_special_characters = True
        
        if not all([has_digits, has_upper_letters, has_special_characters]):
            raise ValueError("Password must contain digits, special symbols, upper letters and be at least 8 characters long")
        
        return self
