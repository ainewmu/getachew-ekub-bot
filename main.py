from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import database as db
from config import ADMIN_PASSWORD
import uvicorn

app = FastAPI(title="Getachew Fikadu Ekub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    await db.init_db()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/vehicles")
async def api_vehicles():
    vehicles = await db.get_vehicles()
    for v in vehicles:
        v["available"] = await db.get_available_count(v["id"])
    return vehicles


@app.get("/api/vehicles/{vehicle_id}")
async def api_vehicle(vehicle_id: int):
    vehicle = await db.get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    vehicle["available"] = await db.get_available_count(vehicle_id)
    return vehicle


@app.get("/api/vehicles/{vehicle_id}/tickets")
async def api_tickets(vehicle_id: int, page: int = 1, per_page: int = 80):
    tickets = await db.get_ticket_status(vehicle_id, page, per_page)
    return tickets


@app.get("/api/banks")
async def api_banks():
    return await db.get_banks()


class OrderCreate(BaseModel):
    user_id: int
    vehicle_id: int
    tickets: List[int]
    full_name: str
    phone: str


@app.post("/api/orders")
async def create_order(order: OrderCreate):
    vehicle = await db.get_vehicle(order.vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    total = vehicle["price"] * len(order.tickets)
    await db.create_order(
        order.user_id, order.vehicle_id, order.tickets,
        total, order.full_name, order.phone
    )
    return {"ok": True, "total": total}


# ---------------- ADMIN ----------------

class AdminLogin(BaseModel):
    password: str


@app.post("/api/admin/login")
async def admin_login(data: AdminLogin):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Wrong password")
    return {"ok": True, "token": "admin-authenticated"}


class VehicleUpdate(BaseModel):
    name: Optional[str] = None
    name_am: Optional[str] = None
    name_or: Optional[str] = None
    subtitle: Optional[str] = None
    price: Optional[int] = None
    total_tickets: Optional[int] = None
    image: Optional[str] = None
    is_active: Optional[int] = None


@app.put("/api/admin/vehicles/{vehicle_id}")
async def admin_update_vehicle(vehicle_id: int, data: VehicleUpdate, x_admin_token: str = Header(None)):
    if x_admin_token != "admin-authenticated":
        raise HTTPException(401, "Unauthorized")
    await db.update_vehicle(vehicle_id, data.dict(exclude_none=True))
    return {"ok": True}


class BankItem(BaseModel):
    name: str
    account: str
    holder: str = ""


class BanksUpdate(BaseModel):
    banks: List[BankItem]


@app.put("/api/admin/banks")
async def admin_update_banks(data: BanksUpdate, x_admin_token: str = Header(None)):
    if x_admin_token != "admin-authenticated":
        raise HTTPException(401, "Unauthorized")
    await db.update_banks([b.dict() for b in data.banks])
    return {"ok": True}


@app.get("/api/admin/vehicles")
async def admin_get_vehicles(x_admin_token: str = Header(None)):
    if x_admin_token != "admin-authenticated":
        raise HTTPException(401, "Unauthorized")
    return await db.get_vehicles()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)