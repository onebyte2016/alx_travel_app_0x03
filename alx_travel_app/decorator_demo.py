# decorator_demo.py

# Basic decorator
def decorator(func): 
    def wrapper():
        print("Before function call")
        func()
        print("After function call")
    return wrapper

@decorator
def say_hello():
    print("Hello!")


# Decorator that calls function twice
def do_twice(func):
    def wrapper_do_twice(*args, **kwargs):
        func(*args, **kwargs)
        func(*args, **kwargs)
    return wrapper_do_twice

@do_twice
def greet(name):
    print(f"Hello {name}")


# Call the functions to see results
say_hello()
greet("Emmanuel")
