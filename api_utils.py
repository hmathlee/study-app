def validate_email(email: str):
    # Modify this later
    return '@' in email


def validate_password(password: str):
    # At least 8 characters, with at least one letter/number
    letters = sum([char.isalpha() for char in password])
    numbers = sum([char.isnumeric() for char in password])
    return len(password) >= 8 and letters >= 1 and numbers >= 1
