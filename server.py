import functools
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.schemas import SchemaGenerator
from datetime import datetime
from shutdowntimer import ShutdownTimer
from lowerpower import start_low_power_service
import uvicorn
import pynput

from middleware import middleware

import asyncio
import random
import time

schemas = SchemaGenerator({"openapi": "3.0.0", "info": {"title": "Deskbot", "version": "1.0"}, "components":
  {"securitySchemes":
    {"basicAuth":
      {"type": "http",
      "scheme": "basic"}
    }
  }
})

current_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(current_dir))#  / "templates"))

app = Starlette(
    debug=True,
    on_startup=None,
    middleware=middleware,
)


@app.route("/", include_in_schema=False)
async def homepage(request):
    context = {
        "time_default": 30,
        "request": request,
    }

    return templates.TemplateResponse(
        name="index.html",
        context=context,
    )

@app.route("/schema", include_in_schema=False, name="openapi_spec")
def openapi_schema(request):
    print(app.routes)
    return JSONResponse(content=schemas.get_schema(app.routes))

@app.route("/docs", include_in_schema=False)
async def swagger_docs(request):
    return templates.TemplateResponse(
        name="swagger.html",
        context={"request": request}
    )


timer = ShutdownTimer()

def authenticate(func):
    @functools.wraps(func)
    async def auth_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

        return await func(request, *args, **kwargs)

    return auth_func

@app.route("/shutdown", methods=["POST"])
@authenticate
async def handle_shutdown_request(request: Request):
    """
    parameters:
    - name: timer
      in: query
      required: true
    responses:
      200:
        description: Start the shutdown timer
    security:
    - basicAuth: []
    """
    time_sch = int(request.query_params.get("timer", -1))
    
    if time_sch >= 0:
        await timer.schedule_shutdown(time_sch)

    return Response(status_code=200)

mouse = pynput.mouse.Controller()
keyboard = pynput.keyboard.Controller()

@app.route("/move", methods=["POST"])
@authenticate
async def handle_move_mouse(request: Request):
    xoff = int(float(request.query_params.get("X", 0)))
    yoff = int(float(request.query_params.get("Y", 0)))
    
    if (xoff or yoff):
        mouse.move(xoff, yoff)
        pass

    return Response(status_code=200)

@app.route("/scroll", methods=["POST"])
@authenticate
async def handle_scroll_mouse(request: Request):
    yoff = int(float(request.query_params.get("Y", 0)))
    
    if yoff:
        mouse.scroll(0, yoff)

    return Response(status_code=200)

@app.route("/volume", methods=["POST"])
@authenticate
async def handle_volume(request: Request):
    voff = int(float(request.query_params.get("V", 0)))
    
    if voff:
        if voff > 0:
            keyboard.press(pynput.keyboard.Key.media_volume_up)
            keyboard.release(pynput.keyboard.Key.media_volume_up)
        else:
            keyboard.press(pynput.keyboard.Key.media_volume_down)
            keyboard.release(pynput.keyboard.Key.media_volume_down)

    return Response(status_code=200)

@app.route("/click", methods=["POST"])
@authenticate
async def handle_click_mouse(request: Request):
    mouse.click(pynput.mouse.Button.left)

    return Response(status_code=200)

@app.route("/middle", methods=["POST"])
@authenticate
async def handle_middle_mouse(request: Request):
    mouse.click(pynput.mouse.Button.middle)

    return Response(status_code=200)

@app.route("/rightclick", methods=["POST"])
@authenticate
async def handle_rightclick_mouse(request: Request):
    mouse.click(pynput.mouse.Button.right)

    return Response(status_code=200)

@app.route("/timer", methods=["GET"])
@authenticate
async def handle_timer(request: Request):
    time_left = await timer.time_left()
    results = {"timer": time_left}

    return JSONResponse(content=results)

@app.route("/cancel", methods=["GET"])
@authenticate
async def cancel_shutdown(request: Request):
    await timer.cancel()

    return Response(status_code=200)

if __name__ == "__main__":
    low_power = start_low_power_service()
    uvicorn.run(app, host="0.0.0.0", port=1337)
    low_power.join()
