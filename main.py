import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException, Header, Form, File, UploadFile
from aiogram.types import BufferedInputFile
from bot import bot, dp
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import database as db
from config import ADMIN_PASSWORD, ADMIN_CHAT_ID
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
    asyncio.create_task(dp.start_polling(bot))


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


@app.get("/api/settings")
async def api_settings():
    return await db.get_settings()


@app.post("/api/orders")
async def create_order(
    user_id: int = Form(0),
    vehicle_id: int = Form(...),
    tickets: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    screenshot: UploadFile = File(...),
):
    vehicle = await db.get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    nums = [int(n) for n in tickets.split(",") if n.strip()]
    if not nums:
        raise HTTPException(400, "No tickets selected")
    total = vehicle["price"] * len(nums)
    await db.create_order(user_id, vehicle_id, nums, total, full_name, phone)

    sent = True
    try:
        text = (
            "🆕 New order\n"
            f"Name: {full_name}\nPhone: {phone}\n"
            f"Car: {vehicle['name']}\n"
            f"Tickets ({len(nums)}): {', '.join('#' + str(n) for n in nums)}\n"
            f"Total: {total:,} Birr\n"
            f"Telegram ID: {user_id}"
        )
        await bot.send_message(ADMIN_CHAT_ID, text[:4000])
        await bot.send_photo(ADMIN_CHAT_ID, BufferedInputFile(await screenshot.read(), filename="payment.jpg"))
    except Exception as e:
        logging.warning(f"Could not send order to admin: {e}")
        sent = False
    return {"ok": True, "total": total, "sent": sent}


# ---------------- ADMIN ----------------

class AdminLogin(BaseModel):
    password: str


@app.post("/api/admin/login")
async def admin_login(data: AdminLogin):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Wrong password")
    return {"ok": True, "token": "admin-authenticated"}


class SettingsUpdate(BaseModel):
    countdown_days: Optional[float] = None
    owner_id_img: Optional[str] = None
    owner_cert_img: Optional[str] = None


@app.put("/api/admin/settings")
async def admin_update_settings(data: SettingsUpdate, x_admin_token: str = Header(None)):
    if x_admin_token != "admin-authenticated":
        raise HTTPException(401, "Unauthorized")
    if data.countdown_days is not None:
        import time
        await db.set_setting("countdown_end", str(int((time.time() + data.countdown_days * 86400) * 1000)))
    for key in ("owner_id_img", "owner_cert_img"):
        val = getattr(data, key)
        if val is not None:
            await db.set_setting(key, val)
    return {"ok": True}


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
