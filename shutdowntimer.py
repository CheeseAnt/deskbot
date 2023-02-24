import asyncio
import subprocess

class ShutdownTimer():
    def __init__(self):
        self.timer = 0
        self.task = None
    
    @property
    def loop(self):
        try:
            return self._loop
        except:
            self._loop = asyncio.get_running_loop()
        
        return self._loop

    def shutdown_computer(self):
        subprocess.call('shutdown /S')
    
    async def schedule_shutdown(self, time):
        if self.task:
            self.task.cancel()

        self.task = self.loop.call_later(time, self.shutdown_computer)
    
    async def time_left(self):
        time = self.loop.time()
        if self.task:
            return self.task.when() - time
        
        return -1

    async def cancel(self):
        if self.task:
            self.task.cancel()
            self.task = None
