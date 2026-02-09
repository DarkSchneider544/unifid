from fastapi import APIRouter

from .endpoints import (
    auth, users, buildings, floor_plans, parking,
    desks, cafeteria, food_orders, attendance, leave,
    it_assets, it_requests, projects, search
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["Buildings"])
api_router.include_router(floor_plans.router, prefix="/floor-plans", tags=["Floor Plans"])
api_router.include_router(parking.router, prefix="/parking", tags=["Parking"])
api_router.include_router(desks.router, prefix="/desks", tags=["Desk Booking"])
api_router.include_router(cafeteria.router, prefix="/cafeteria", tags=["Cafeteria"])
api_router.include_router(food_orders.router, prefix="/food-orders", tags=["Food Orders"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
api_router.include_router(leave.router, prefix="/leave", tags=["Leave Management"])
api_router.include_router(it_assets.router, prefix="/it-assets", tags=["IT Assets"])
api_router.include_router(it_requests.router, prefix="/it-requests", tags=["IT Requests"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])