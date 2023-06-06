import pynput
import asyncio
import subprocess
import time
import threading
import winreg

INACTIVITY_TIME = 60 * 15
DETACHED_PROCESS = 0x00000008


class PowerTimer():
    NOMINAL_PLAN_LOC = "nominal_power_plan.pln"

    def __init__(self):
        self.timer = 0
        self.task = None
        self.registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        self.power_key = winreg.OpenKey(self.registry, r"SYSTEM\ControlSet001\Control\Power\User\PowerSchemes")
        self.old_power_hash = None
        self.low_power_hash = 'a1841308-3541-4fab-bc81-f71556f20b4a'
        self.mutex = asyncio.Lock()

    @property
    def loop(self):
        try:
            return self._loop
        except:
            self._loop = asyncio.get_running_loop()
        
        return self._loop

    def change_power_plan(self, plan=None):
        if plan is None:
            plan = self.low_power_hash
            self.get_current_plan()
        
        print(f"Going to plan {plan}")

        subprocess.call(f'POWERCFG /SETACTIVE {plan}', creationflags=DETACHED_PROCESS)
    
    def get_nominal_plan(self):
        with open(PowerTimer.NOMINAL_PLAN_LOC, 'r') as f:
            return f.read()
    
    def set_nominal_plan(self, plan: str):
        with open(self.NOMINAL_PLAN_LOC, 'w') as f:
            f.write(plan)

    def get_current_plan(self):
        self.old_power_hash = winreg.QueryValueEx(self.power_key, 'ActivePowerScheme')[0]

        if self.old_power_hash != self.low_power_hash:
            self.set_nominal_plan(self.old_power_hash)
        else:
            self.old_power_hash = self.get_nominal_plan()

        print(f"saving {self.old_power_hash}")
    
    async def schedule_low_power(self, time=INACTIVITY_TIME):
        async with self.mutex:
            if self.task:
                self.task.cancel()

            if self.old_power_hash:
                self.change_power_plan(plan=self.old_power_hash)
                self.old_power_hash = None
        
            self.task = self.loop.call_later(time, self.change_power_plan)
    
    async def time_left(self):
        time = self.loop.time()
        if self.task:
            return self.task.when() - time
        
        return -1

    async def cancel(self):
        if self.task:
            self.task.cancel()
            self.task = None

def activity_detector(event_class: pynput._util.Events, user_event: threading.Event):
    with event_class() as events:
        while True:
            event = events.get()

            user_event.set()

            time.sleep(5)

            with events._event_queue.mutex:
                events._event_queue.queue.clear()

def power_service(user_event: threading.Event):
    async def asyncmain():
        powmon = PowerTimer()
        await powmon.schedule_low_power()

        while True:
            if user_event.is_set():
                await powmon.schedule_low_power()
                user_event.clear()
            
            await asyncio.sleep(0.1)
    
    asyncio.run(asyncmain())

def reset_power():
    PowerTimer.change_power_plan(None, plan=PowerTimer.get_nominal_plan(None))

def start_low_power_service() -> threading.Thread:
    def outer_thread():
        user_event = threading.Event()
        reset_power()

        mouse = threading.Thread(target=activity_detector, args=(pynput.mouse.Events, user_event), daemon=True)
        keyboard = threading.Thread(target=activity_detector, args=(pynput.keyboard.Events, user_event), daemon=True)
        service = threading.Thread(target=power_service, args=(user_event, ), daemon=True)
        mouse.start()
        keyboard.start()
        service.start()
        mouse.join()
        keyboard.join()
        service.join()
    
    outer_service = threading.Thread(target=outer_thread)
    outer_service.start()

    return outer_service

if __name__ == '__main__':
    start_low_power_service().join()
