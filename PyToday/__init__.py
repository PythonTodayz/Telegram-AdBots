#__init__.py fixed by @otterai 
"""
Central export hub for PyToday package.
Allows importing everything from all modules using:
    from PyToday import *
or selective imports when needed.
"""

# ---- core modules (as modules) ----
from . import config
from . import database
from . import telethon_handler
from . import handlers
from . import keyboards

# ----  important functions / objects ----
from .encryption import encrypt_data, decrypt_data

# ---- export everything from submodules ----
from .config import *
from .database import *
from .telethon_handler import *
from .handlers import *
from .keyboards import *

# ---- public API ----
__all__ = [
    
    "config",
    "database",
    "telethon_handler",
    "handlers",
    "keyboards",

    # encryption helpers
    "encrypt_data",
    "decrypt_data",
]

# auto-export all UPPERCASE config vars
__all__ += [name for name in globals() if name.isupper()]
