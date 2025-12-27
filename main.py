import os


def main():
    my_secret_token = os.getenv('MY_SECRET_TOKEN')
    print("Hello from super-yaya-agents! here is the test MY_SECRET_TOKEN", my_secret_token)


if __name__ == "__main__":
    main()
