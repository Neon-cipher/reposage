from sample_repo.src.utils import add_numbers

def run_pipeline(x: int, y: int) -> int:
    """Run core processing logic."""
    # TODO: Add caching layer for repeated calculations
    return add_numbers(x, y)

if __name__ == '__main__':
    result = run_pipeline(10, 20)
    print(f"Result: {result}")
