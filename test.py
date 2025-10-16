
import asyncio

async def test1():
    for _ in range(10):
        print("test1")
        await asyncio.sleep(1)

async def test2():
    for _ in range(10):
        print("test2")
        await asyncio.sleep(4)

async def main():
    # Run both tasks concurrently
    await asyncio.gather(test1(), test2())

if __name__ == '__main__':
    asyncio.run(main())
