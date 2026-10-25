"""
Compatibility layer for Starlette and FastAPI version transitions.

Ensures Starlette Router and Applications safely handle legacy on_startup,
on_shutdown, add_event_handler, and max_body_size attributes passed or accessed
between FastAPI and newer Starlette releases.
"""

import inspect
import starlette.routing
import starlette.applications

# Ensure Starlette application class has default max_body_size attribute
if not hasattr(starlette.applications.Starlette, "max_body_size"):
    starlette.applications.Starlette.max_body_size = None

_orig_router_init = starlette.routing.Router.__init__
_sig = inspect.signature(_orig_router_init)

def _compat_router_init(self, *args, **kwargs):
    on_startup = kwargs.pop("on_startup", None)
    on_shutdown = kwargs.pop("on_shutdown", None)
    self.on_startup = [] if on_startup is None else list(on_startup)
    self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
    return _orig_router_init(self, *args, **kwargs)

starlette.routing.Router.__init__ = _compat_router_init

if not hasattr(starlette.routing.Router, "add_event_handler"):
    def _add_event_handler(self, event_type: str, func):
        if not hasattr(self, "on_startup"):
            self.on_startup = []
        if not hasattr(self, "on_shutdown"):
            self.on_shutdown = []
        if event_type == "startup":
            self.on_startup.append(func)
        elif event_type == "shutdown":
            self.on_shutdown.append(func)
    starlette.routing.Router.add_event_handler = _add_event_handler
