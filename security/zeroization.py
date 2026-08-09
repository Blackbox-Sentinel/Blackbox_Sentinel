def execute_zeroization(secrets):

    print("\nStarting Zeroization...")

    for key in secrets:

        value = secrets[key]

        if isinstance(value, bytearray):
            for i in range(len(value)):
                value[i] = 0

        else:
            secrets[key] = None

    print("Sensitive data destroyed.")

    return True

if __name__ == "__main__":

    secrets = {
        "api_key": bytearray(b"MY_SECRET_API_KEY"),
        "password": bytearray(b"SuperPassword123"),
        "session_token": bytearray(b"abcdef123456")
    }

    print("Before:")
    print(secrets)

    execute_zeroization(secrets)

    print("\nAfter:")
    print(secrets)