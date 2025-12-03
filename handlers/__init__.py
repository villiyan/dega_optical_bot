from .user_handler import router as user_router
from .admin_handler import router as admin_router

routers = [user_router, admin_router]
