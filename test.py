import types

async def example_gen():
    yield 1
    yield 2

gen = example_gen()

print(type(gen))
# Check if it's a generator
print(isinstance(gen, types.AsyncGeneratorType))  # True

# Check for a normal list (not a generator)
print(isinstance([1, 2, 3], types.AsyncGeneratorType))  # False
