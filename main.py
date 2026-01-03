import os


def main():
    my_secret_token = os.getenv("MY_SECRET_TOKEN")
    if my_secret_token == "HelloWorld":
        print("i read correct value")
    else:
        print("i read incorrect value: lol")
    print("Hello from super-yaya-agents! here is the test MY_SECRET_TOKEN", my_secret_token)


if __name__ == "__main__":
    main()
