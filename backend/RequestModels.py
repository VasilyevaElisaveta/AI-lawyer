from pydantic import BaseModel, Field, model_validator
from string import punctuation, ascii_uppercase, digits
from re import fullmatch


class RegistrationRequestModel(BaseModel):

    model_config = {"extra": "forbid"}

    name: str
    surname: str
    patronymic: str | None
    username: str
    email: str
    password: str = Field(min_length=8)
    user_agreement_accepted: bool
    personal_data_processing_accepted: bool

    @model_validator(mode="after")
    def validate_agreements(self):
        if not self.user_agreement_accepted or not self.personal_data_processing_accepted:
            raise ValueError("The user must accept the user agreement and the personal data processing policy before registration.")
        return self
    
    @model_validator(mode="after")
    def validate_email(self):
        email_re = r"[a-zA-Z0-9]+[a-zA-Z0-9.-_]+@[a-z]+\.[a-z]+"
        if fullmatch(email_re, self.email) is None:
            raise ValueError(f"{self.email} is not an email.")
        return self

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
