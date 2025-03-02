import arguably

@arguably.command
def hello(name: str = "World"):
    """
    A simple hello world command.
    
    Args:
        name: The name to greet (defaults to "World")
    """
    print(f"Helloooo, {name}!")

if __name__ == "__main__":
    arguably.run() 
