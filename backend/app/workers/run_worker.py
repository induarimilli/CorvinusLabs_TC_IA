from app.workers.provisioning import run_worker

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_worker())
