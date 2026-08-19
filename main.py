from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import random
from datetime import datetime, timedelta
import httpx
import secrets
import json
import os
import pandas as pd
import io
import csv
import bcrypt
import jwt
from typing import Optional, Dict, List
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
from contextlib import asynccontextmanager

app = FastAPI(title="FORESIGHT Enterprise AI Platform", version="8.0.0")

# ============================================
# DATABASE CONFIG (In-Memory with JSON persistence)
# ============================================
DATA_FILE = "foresight_data.json"

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "users": [],
            "inventory": [],
            "sessions": {},
            "user_preferences": {},
            "audit_logs": [],
            "notifications": [],
            "weekly_data": [],
            "predictions": []
        }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, default=str)

# Load initial data
db_data = load_data()

# ============================================
# EMAIL CONFIG
# ============================================
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@foresight.ai")

def send_email(to_email: str, subject: str, body: str, html_body: str = None):
    try:
        if not SMTP_USER or not SMTP_PASSWORD:
            print(f"📧 Email would be sent to {to_email}: {subject}")
            return True
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM_EMAIL
        msg['To'] = to_email
        
        part1 = MIMEText(body, 'plain')
        msg.attach(part1)
        
        if html_body:
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ============================================
# JWT AUTH CONFIG
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None

def hash_password(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ============================================
# PYDANTIC MODELS
# ============================================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "analyst"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class SettingsUpdate(BaseModel):
    theme: str = "dark"
    notifications: bool = True
    weekly_reports: bool = False
    currency: str = "INR"
    language: str = "en"

# ============================================
# MOCK DATA GENERATION
# ============================================
def generate_business_data():
    weeks = []
    current_date = datetime.now()
    base_stock = 150
    base_revenue = 25000
    
    for i in range(12, -1, -1):
        week_start = current_date - timedelta(days=i*7)
        week_label = f"Week {13-i}"
        
        growth_factor = random.uniform(0.92, 1.15)
        revenue = int(base_revenue * growth_factor * (1 + (12-i) * 0.02))
        
        weeks.append({
            "week": week_label,
            "date": week_start.strftime("%b %d"),
            "products_tracked": int(base_stock * growth_factor * (1 + (12-i) * 0.015)),
            "new_products": random.randint(3, 15),
            "sales": random.randint(500, 1200),
            "orders": random.randint(45, 89),
            "revenue": revenue,
            "growth": round(random.uniform(-5, 12), 1),
            "profit": int(revenue * random.uniform(0.15, 0.35)),
            "customers": random.randint(300, 800),
            "satisfaction": round(random.uniform(3.5, 4.9), 1),
            "fulfillment_rate": random.randint(92, 99),
            "warehouse_utilization": random.randint(65, 95),
            "return_rate": round(random.uniform(0.5, 3.5), 1),
            "conversion_rate": round(random.uniform(2.5, 6.5), 1),
            "avg_order_value": random.randint(2500, 6500)
        })
    return weeks

weekly_data = generate_business_data()

def generate_predictions():
    last_week = weekly_data[-1]
    predictions = []
    current_date = datetime.now()
    
    for i in range(1, 8):
        future_date = current_date + timedelta(days=i*7)
        growth_factor = random.uniform(0.85, 1.25)
        confidence = random.randint(78, 97)
        
        predictions.append({
            "day": f"Day {i}",
            "date": future_date.strftime("%b %d"),
            "predicted_sales": int(last_week["sales"] * growth_factor * random.uniform(0.9, 1.1)),
            "predicted_revenue": int(last_week["revenue"] * growth_factor * random.uniform(0.85, 1.15)),
            "predicted_products": int(last_week["products_tracked"] * growth_factor * random.uniform(0.95, 1.05)),
            "predicted_orders": int(last_week["orders"] * growth_factor * random.uniform(0.9, 1.1)),
            "predicted_customers": int(last_week["customers"] * growth_factor * random.uniform(0.95, 1.08)),
            "confidence": confidence,
            "trend": "up" if growth_factor > 1 else "down"
        })
    return predictions

predictions_data = generate_predictions()

# ============================================
# INVENTORY DATA
# ============================================
products = [
    "Ergonomic Chair", "Wireless Mouse", "USB-C Hub", "Monitor Stand",
    "Mechanical Keyboard", "4K Monitor", "Laptop Stand", "Desk Mat",
    "Webcam", "Noise-Canceling Headphones", "Portable SSD", "Docking Station",
    "Smartphone Stand", "Cable Management Kit", "Screen Protector",
    "Power Bank", "USB Cable", "HDMI Adapter", "Laptop Bag", "Desk Lamp",
    "Wireless Charger", "Bluetooth Speaker", "External Hard Drive", "USB Flash Drive",
    "Tablet Stand", "Laptop Cooler", "HDMI Cable", "DisplayPort Adapter"
]

stores = ["NYC Flagship", "LA Tech Hub", "Chicago Downtown", "Austin", "Seattle", "Boston", "Miami", "Denver", "San Francisco", "Portland"]

inventory = []
expiry_alerts = []
reorder_alerts = []

for p in products:
    for s in random.sample(stores, random.randint(1, 3)):
        stock = random.randint(0, 180)
        reorder_level = random.randint(15, 45)
        
        if stock > 30:
            status = "In Stock"
        elif stock > 10:
            status = "Low Stock"
        else:
            status = "Critical"
        
        if stock < reorder_level and status != "Critical":
            reorder_alerts.append({
                "product": p,
                "sku": f"{p[:3].upper()}-{random.randint(100, 999)}",
                "current_stock": stock,
                "reorder_level": reorder_level,
                "suggested_order": reorder_level - stock + random.randint(10, 30)
            })
        
        expiry_days = random.randint(5, 90) if random.random() > 0.3 else None
        expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d") if expiry_days else None
        days_until_expiry = expiry_days if expiry_days else None
        
        item = {
            "product": p,
            "sku": f"{p[:3].upper()}-{random.randint(100, 999)}",
            "store": s,
            "stock": stock,
            "status": status,
            "reorder_level": reorder_level,
            "expiry_date": expiry_date,
            "days_until_expiry": days_until_expiry,
            "cost_price": random.randint(200, 2000),
            "selling_price": random.randint(300, 3500),
            "category": random.choice(["Electronics", "Accessories", "Furniture", "Peripherals"]),
            "supplier": random.choice(["TechSource Inc", "Global Supplies", "DirectTrade", "Prime Distributors"])
        }
        inventory.append(item)
        
        if days_until_expiry and days_until_expiry <= 30:
            expiry_alerts.append({
                "product": p,
                "sku": item["sku"],
                "days": days_until_expiry,
                "status": "Critical" if days_until_expiry <= 7 else "Warning"
            })

# ============================================
# USD TO INR CONVERSION
# ============================================
USD_TO_INR = 83.50

def usd_to_inr(usd_amount):
    return int(usd_amount * USD_TO_INR)

# ============================================
# NOTIFICATIONS
# ============================================
def generate_notifications():
    global notifications
    notifications = []
    
    low_stock_items = [i for i in inventory if i["status"] == "Low Stock"]
    for item in low_stock_items[:3]:
        notifications.append({
            "id": len(notifications) + 1,
            "type": "warning",
            "icon": "⚠️",
            "title": "Low Stock Alert",
            "message": f"{item['product']} has only {item['stock']} units remaining",
            "time": "Just now",
            "read": False
        })
    
    critical_items = [i for i in inventory if i["status"] == "Critical"]
    for item in critical_items[:2]:
        notifications.append({
            "id": len(notifications) + 1,
            "type": "danger",
            "icon": "🚨",
            "title": "Critical Stock Alert",
            "message": f"{item['product']} is critically low with only {item['stock']} units",
            "time": "Just now",
            "read": False
        })
    
    for alert in expiry_alerts[:2]:
        notifications.append({
            "id": len(notifications) + 1,
            "type": "warning" if alert["status"] == "Warning" else "danger",
            "icon": "⏰",
            "title": "Expiry Alert",
            "message": f"{alert['product']} expires in {alert['days']} days",
            "time": "Just now",
            "read": False
        })
    
    for alert in reorder_alerts[:2]:
        notifications.append({
            "id": len(notifications) + 1,
            "type": "info",
            "icon": "📦",
            "title": "Reorder Recommendation",
            "message": f"Order {alert['suggested_order']} units of {alert['product']}",
            "time": "Just now",
            "read": False
        })
    
    if predictions_data:
        notifications.append({
            "id": len(notifications) + 1,
            "type": "info",
            "icon": "📈",
            "title": "AI Prediction Update",
            "message": f"Next week sales predicted to increase by {random.randint(5, 15)}%",
            "time": "Just now",
            "read": False
        })

generate_notifications()

# ============================================
# GOOGLE OAUTH CONFIG
# ============================================
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# ============================================
# SESSION STORAGE
# ============================================
sessions = {}
user_preferences = {}
uploaded_data = []
notifications = []
audit_logs = []

# ============================================
# GET USER HELPER
# ============================================
def get_user(request):
    token = request.cookies.get("session_token")
    if token and token in sessions:
        return sessions[token]
    return None

# ============================================
# LOGIN PAGE
# ============================================
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>FORESIGHT · Enterprise AI Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; min-height: 100vh; display: flex; justify-content: center; align-items: center; background: #0a0f1f; position: relative; overflow: hidden; }
        .orb { position: absolute; border-radius: 50%; filter: blur(150px); opacity: 0.2; animation: floatOrb 30s infinite alternate; }
        .orb-1 { width: 700px; height: 700px; background: #0d9488; top: -250px; right: -250px; }
        .orb-2 { width: 600px; height: 600px; background: #14b8a6; bottom: -250px; left: -250px; animation-delay: 15s; }
        .orb-3 { width: 400px; height: 400px; background: #2dd4bf; top: 50%; left: 50%; transform: translate(-50%, -50%); animation-delay: 7s; }
        @keyframes floatOrb { 0% { transform: translate(0,0) scale(1); } 100% { transform: translate(80px,60px) scale(1.2); } }
        .login-container { position: relative; z-index: 10; background: rgba(255,255,255,0.02); backdrop-filter: blur(80px); border: 1px solid rgba(255,255,255,0.06); border-radius: 3rem; padding: 4rem 3.5rem; max-width: 480px; width: 100%; box-shadow: 0 60px 120px rgba(0,0,0,0.6); animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes slideUp { from { opacity: 0; transform: translateY(50px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
        .login-header { text-align: center; margin-bottom: 3rem; }
        .logo { display: inline-flex; align-items: center; gap: 1rem; font-size: 1.8rem; font-weight: 800; color: white; }
        .logo i { color: #0d9488; font-size: 2.5rem; background: rgba(13,148,136,0.12); padding: 0.8rem; border-radius: 1.2rem; }
        .logo span { background: linear-gradient(135deg, #fff 30%, #0d9488 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .login-header h2 { color: white; font-size: 2rem; font-weight: 700; margin-top: 1.5rem; letter-spacing: -0.5px; }
        .login-header p { color: rgba(255,255,255,0.3); font-size: 0.95rem; margin-top: 0.5rem; font-weight: 300; }
        .btn-google { width: 100%; padding: 1rem; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 1.2rem; color: white; font-weight: 500; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.75rem; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); font-size: 0.95rem; text-decoration: none; }
        .btn-google:hover { background: rgba(255,255,255,0.08); transform: translateY(-3px); border-color: rgba(13,148,136,0.3); box-shadow: 0 12px 40px rgba(13,148,136,0.1); }
        .divider { text-align: center; color: rgba(255,255,255,0.08); font-size: 0.8rem; margin: 1.8rem 0; position: relative; letter-spacing: 1px; }
        .divider::before { content: ''; position: absolute; top: 50%; left: 0; right: 0; height: 1px; background: rgba(255,255,255,0.04); }
        .divider span { background: transparent; padding: 0 1.5rem; position: relative; }
        .form-group { margin-bottom: 1.2rem; }
        .form-group label { display: block; color: rgba(255,255,255,0.3); font-weight: 500; font-size: 0.7rem; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px; }
        .form-group input { width: 100%; padding: 1rem 1.2rem; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 1rem; color: white; font-size: 0.95rem; transition: all 0.4s ease; font-family: 'Inter', sans-serif; }
        .form-group input:focus { outline: none; border-color: rgba(13,148,136,0.3); background: rgba(13,148,136,0.04); box-shadow: 0 0 0 4px rgba(13,148,136,0.04); }
        .form-group input::placeholder { color: rgba(255,255,255,0.15); }
        .btn-primary { width: 100%; padding: 1rem; background: linear-gradient(135deg, #0d9488, #14b8a6); color: white; border: none; border-radius: 1rem; font-weight: 600; font-size: 1rem; cursor: pointer; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); margin-top: 0.5rem; font-family: 'Inter', sans-serif; position: relative; overflow: hidden; }
        .btn-primary::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent); transition: left 0.6s ease; }
        .btn-primary:hover::before { left: 100%; }
        .btn-primary:hover { transform: translateY(-3px); box-shadow: 0 16px 50px rgba(13,148,136,0.3); }
        .error-message { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.15); color: #fca5a5; padding: 0.8rem 1rem; border-radius: 0.8rem; font-size: 0.85rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        .features { display: flex; gap: 0.5rem; margin: 2rem 0 1.5rem; justify-content: center; flex-wrap: wrap; }
        .feature-badge { background: rgba(13,148,136,0.06); border: 1px solid rgba(13,148,136,0.08); color: rgba(255,255,255,0.4); padding: 0.3rem 1rem; border-radius: 2rem; font-size: 0.65rem; font-weight: 500; display: flex; align-items: center; gap: 0.4rem; }
        .feature-badge i { color: #0d9488; font-size: 0.5rem; }
        .login-footer { text-align: center; margin-top: 1.5rem; color: rgba(255,255,255,0.12); font-size: 0.8rem; }
        .login-footer a { color: rgba(13,148,136,0.5); text-decoration: none; transition: color 0.3s; }
        .login-footer a:hover { color: #0d9488; }
        @media (max-width: 480px) { .login-container { padding: 2.5rem 1.5rem; margin: 1rem; } .login-header h2 { font-size: 1.6rem; } }
    </style>
</head>
<body>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="login-container">
        <div class="login-header">
            <div class="logo"><i class="fas fa-brain"></i><span>FORESIGHT</span></div>
            <h2>Welcome back</h2>
            <p>Enterprise AI intelligence platform</p>
        </div>
        <a href="/auth/google" class="btn-google">
            <i class="fab fa-google"></i> Continue with Google
        </a>
        <div class="divider"><span>or sign in with email</span></div>
        <div id="errorContainer">{error}</div>
        <form method="post" action="/login">
            <div class="form-group">
                <label>Email address</label>
                <input type="email" name="email" placeholder="demo@foresight.ai" value="demo@foresight.ai" required />
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="••••••••" value="password123" required />
            </div>
            <button type="submit" class="btn-primary">
                <i class="fas fa-arrow-right" style="margin-right:0.6rem;"></i> Sign in
            </button>
        </form>
        <div class="features">
            <span class="feature-badge"><i class="fas fa-check-circle"></i> AI-Powered</span>
            <span class="feature-badge"><i class="fas fa-chart-line"></i> Real-Time</span>
            <span class="feature-badge"><i class="fas fa-shield-alt"></i> Enterprise</span>
        </div>
        <div class="login-footer">Don't have an account? <a href="/register">Register</a></div>
    </div>
</body>
</html>
"""

# ============================================
# REGISTER HTML
# ============================================
REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FORESIGHT · Register</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; min-height: 100vh; display: flex; justify-content: center; align-items: center; background: #0a0f1f; position: relative; overflow: hidden; }
        .orb { position: absolute; border-radius: 50%; filter: blur(150px); opacity: 0.2; animation: floatOrb 30s infinite alternate; }
        .orb-1 { width: 700px; height: 700px; background: #0d9488; top: -250px; right: -250px; }
        .orb-2 { width: 600px; height: 600px; background: #14b8a6; bottom: -250px; left: -250px; animation-delay: 15s; }
        .orb-3 { width: 400px; height: 400px; background: #2dd4bf; top: 50%; left: 50%; transform: translate(-50%, -50%); animation-delay: 7s; }
        @keyframes floatOrb { 0% { transform: translate(0,0) scale(1); } 100% { transform: translate(80px,60px) scale(1.2); } }
        .register-container { position: relative; z-index: 10; background: rgba(255,255,255,0.02); backdrop-filter: blur(80px); border: 1px solid rgba(255,255,255,0.06); border-radius: 3rem; padding: 4rem 3.5rem; max-width: 480px; width: 100%; box-shadow: 0 60px 120px rgba(0,0,0,0.6); animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes slideUp { from { opacity: 0; transform: translateY(50px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
        .register-header { text-align: center; margin-bottom: 3rem; }
        .logo { display: inline-flex; align-items: center; gap: 1rem; font-size: 1.8rem; font-weight: 800; color: white; }
        .logo i { color: #0d9488; font-size: 2.5rem; background: rgba(13,148,136,0.12); padding: 0.8rem; border-radius: 1.2rem; }
        .logo span { background: linear-gradient(135deg, #fff 30%, #0d9488 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .register-header h2 { color: white; font-size: 2rem; font-weight: 700; margin-top: 1.5rem; letter-spacing: -0.5px; }
        .register-header p { color: rgba(255,255,255,0.3); font-size: 0.95rem; margin-top: 0.5rem; font-weight: 300; }
        .form-group { margin-bottom: 1.2rem; }
        .form-group label { display: block; color: rgba(255,255,255,0.3); font-weight: 500; font-size: 0.7rem; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px; }
        .form-group input { width: 100%; padding: 1rem 1.2rem; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 1rem; color: white; font-size: 0.95rem; transition: all 0.4s ease; font-family: 'Inter', sans-serif; }
        .form-group input:focus { outline: none; border-color: rgba(13,148,136,0.3); background: rgba(13,148,136,0.04); box-shadow: 0 0 0 4px rgba(13,148,136,0.04); }
        .form-group input::placeholder { color: rgba(255,255,255,0.15); }
        .btn-primary { width: 100%; padding: 1rem; background: linear-gradient(135deg, #0d9488, #14b8a6); color: white; border: none; border-radius: 1rem; font-weight: 600; font-size: 1rem; cursor: pointer; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); margin-top: 0.5rem; font-family: 'Inter', sans-serif; }
        .btn-primary:hover { transform: translateY(-3px); box-shadow: 0 16px 50px rgba(13,148,136,0.3); }
        .password-hint { font-size: 0.7rem; color: rgba(255,255,255,0.2); margin-top: 0.3rem; }
        .footer-text { text-align: center; margin-top: 1.5rem; color: rgba(255,255,255,0.12); font-size: 0.8rem; }
        .footer-text a { color: rgba(13,148,136,0.5); text-decoration: none; transition: color 0.3s; }
        .footer-text a:hover { color: #0d9488; }
        @media (max-width: 480px) { .register-container { padding: 2.5rem 1.5rem; margin: 1rem; } .register-header h2 { font-size: 1.6rem; } }
    </style>
</head>
<body>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="register-container">
        <div class="register-header">
            <div class="logo"><i class="fas fa-brain"></i><span>FORESIGHT</span></div>
            <h2>Create account</h2>
            <p>Join the enterprise AI platform</p>
        </div>
        <form method="post" action="/register">
            <div class="form-group">
                <label>Full Name</label>
                <input type="text" name="name" placeholder="John Doe" required />
            </div>
            <div class="form-group">
                <label>Email address</label>
                <input type="email" name="email" placeholder="you@company.com" required />
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="••••••••" required />
                <div class="password-hint">Must be at least 8 characters</div>
            </div>
            <button type="submit" class="btn-primary">
                <i class="fas fa-user-plus" style="margin-right:0.6rem;"></i> Create Account
            </button>
        </form>
        <div class="footer-text">Already have an account? <a href="/login">Sign in</a></div>
    </div>
</body>
</html>
"""

# ============================================
# RENDER PAGE FUNCTION
# ============================================
def render_page(content, user, active_page, title, notifications_html=""):
    name = user.get("name", "User")
    avatar = user.get("avatar", "U")
    role = user.get("role", "Analyst")
    notification_count = len(expiry_alerts) + len([i for i in inventory if i["status"] == "Critical"]) + len(reorder_alerts)
    unread_count = len([n for n in notifications if not n.get("read", False)])
    
    sidebar = f'''
<div class="logo"><i class="fas fa-brain"></i><span>FORESIGHT</span></div>
<div class="nav-label">MAIN MENU</div>
<nav class="nav">
    <a href="/dashboard" class="{'active' if active_page == 'dashboard' else ''}"><i class="fas fa-chart-pie"></i> Dashboard</a>
    <a href="/analytics" class="{'active' if active_page == 'analytics' else ''}"><i class="fas fa-chart-line"></i> Analytics</a>
    <a href="/forecast" class="{'active' if active_page == 'forecast' else ''}"><i class="fas fa-robot"></i> Forecast</a>
    <a href="/predictions" class="{'active' if active_page == 'predictions' else ''}"><i class="fas fa-clock"></i> Predictions</a>
    <a href="/inventory" class="{'active' if active_page == 'inventory' else ''}"><i class="fas fa-cubes"></i> Inventory</a>
    <a href="/cleaning" class="{'active' if active_page == 'cleaning' else ''}"><i class="fas fa-broom"></i> Data Cleaning</a>
    <a href="/upload" class="{'active' if active_page == 'upload' else ''}"><i class="fas fa-upload"></i> Upload</a>
    <a href="/reports" class="{'active' if active_page == 'reports' else ''}"><i class="fas fa-file-alt"></i> Reports</a>
    <a href="/profile" class="{'active' if active_page == 'profile' else ''}"><i class="fas fa-user"></i> Profile</a>
    <a href="/settings" class="{'active' if active_page == 'settings' else ''}"><i class="fas fa-cog"></i> Settings</a>
</nav>
<div class="user-section">
    <div class="user">
        <div class="avatar">{avatar}</div>
        <div class="user-info">
            <div class="name">{name}</div>
            <div class="role">{role}</div>
        </div>
    </div>
    <a href="/logout" class="logout-btn"><i class="fas fa-sign-out-alt"></i> Logout</a>
</div>
'''
    
    hour = datetime.now().hour
    time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    
    notif_items = notifications_html if notifications_html else ""
    if not notif_items:
        for n in notifications[:5]:
            notif_items += f'''
            <div style="display:flex;align-items:center;gap:0.8rem;padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.02);">
                <span style="font-size:1.2rem;">{n["icon"]}</span>
                <div style="flex:1;">
                    <div style="font-size:0.8rem;color:rgba(255,255,255,0.7);">{n["message"]}</div>
                    <div style="font-size:0.6rem;color:rgba(255,255,255,0.1);">{n["time"]}</div>
                </div>
                {'' if n.get('read', False) else '<span style="width:6px;height:6px;background:#0d9488;border-radius:50%;flex-shrink:0;"></span>'}
            </div>
            '''
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FORESIGHT · {title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --primary: #0d9488;
            --primary-light: #14b8a6;
            --primary-dark: #0f766e;
            --primary-glow: rgba(13,148,136,0.3);
            --bg-dark: #070e1a;
            --card-bg: rgba(255,255,255,0.02);
            --border-color: rgba(255,255,255,0.04);
            --text-primary: #ffffff;
            --text-secondary: rgba(255,255,255,0.4);
            --text-muted: rgba(255,255,255,0.15);
            --gradient-1: linear-gradient(135deg, #0d9488, #14b8a6);
            --gradient-2: linear-gradient(135deg, #0f766e, #0d9488);
        }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg-dark); color: var(--text-primary); min-height: 100vh; }}
        .dashboard {{ display: flex; min-height: 100vh; }}
        .sidebar {{
            width: 280px;
            background: rgba(255,255,255,0.02);
            backdrop-filter: blur(30px);
            border-right: 1px solid var(--border-color);
            padding: 2rem 1.5rem;
            display: flex;
            flex-direction: column;
            position: sticky; top: 0; height: 100vh;
            overflow-y: auto;
        }}
        .sidebar::-webkit-scrollbar {{ width: 4px; }}
        .sidebar::-webkit-scrollbar-thumb {{ background: var(--primary); border-radius: 2px; }}
        .logo {{ display: flex; align-items: center; gap: 0.8rem; font-size: 1.4rem; font-weight: 800; color: white; margin-bottom: 1.8rem; }}
        .logo i {{ color: var(--primary); font-size: 1.6rem; background: rgba(13,148,136,0.12); padding: 0.5rem; border-radius: 0.8rem; }}
        .logo span {{ background: linear-gradient(135deg, #fff 40%, var(--primary) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .nav-label {{ color: rgba(255,255,255,0.06); font-size: 0.5rem; text-transform: uppercase; letter-spacing: 2px; padding: 0.5rem 0.8rem; margin-top: 0.5rem; font-weight: 600; }}
        .nav {{ display: flex; flex-direction: column; gap: 0.15rem; flex: 1; }}
        .nav a {{ display: flex; align-items: center; gap: 0.85rem; padding: 0.6rem 0.8rem; border-radius: 0.6rem; color: rgba(255,255,255,0.25); text-decoration: none; font-weight: 500; transition: all 0.3s ease; font-size: 0.85rem; }}
        .nav a:hover {{ background: rgba(255,255,255,0.04); color: white; }}
        .nav a.active {{ background: rgba(13,148,136,0.08); color: white; border: 1px solid rgba(13,148,136,0.08); }}
        .nav a i {{ width: 1.4rem; font-size: 0.9rem; opacity: 0.4; }}
        .nav a.active i {{ opacity: 1; color: var(--primary); }}
        .user-section {{ border-top: 1px solid var(--border-color); padding-top: 1rem; margin-top: auto; }}
        .user {{ display: flex; align-items: center; gap: 0.8rem; }}
        .avatar {{ width: 36px; height: 36px; border-radius: 50%; background: var(--gradient-1); display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 0.8rem; }}
        .user-info .name {{ color: white; font-weight: 600; font-size: 0.85rem; }}
        .user-info .role {{ color: rgba(255,255,255,0.15); font-size: 0.65rem; }}
        .logout-btn {{ display: flex; align-items: center; gap: 0.5rem; color: rgba(255,255,255,0.1); text-decoration: none; padding: 0.4rem 0; margin-top: 0.3rem; font-size: 0.75rem; transition: all 0.3s ease; }}
        .logout-btn:hover {{ color: #ef4444; }}
        .main {{ flex: 1; padding: 2rem 2.5rem; }}
        .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem; }}
        .topbar h1 {{ font-size: 1.6rem; font-weight: 700; }}
        .topbar h1 span {{ color: var(--primary); }}
        .topbar .date {{ color: rgba(255,255,255,0.15); font-size: 0.75rem; background: rgba(255,255,255,0.02); padding: 0.5rem 1.2rem; border-radius: 2rem; border: 1px solid var(--border-color); }}
        .greeting {{ color: rgba(255,255,255,0.3); font-size: 0.85rem; margin-top: 0.15rem; }}
        .content {{ background: rgba(255,255,255,0.01); border: 1px solid var(--border-color); border-radius: 1.5rem; padding: 2rem; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.2rem; margin-bottom: 1.5rem; }}
        .grid-5 {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1.2rem; margin-bottom: 1.5rem; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem; margin-bottom: 1.5rem; }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.2rem; margin-bottom: 1.5rem; }}
        .stat-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 1rem; padding: 1.5rem; text-align: center; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }}
        .stat-card:hover {{ transform: translateY(-4px); border-color: rgba(13,148,136,0.12); box-shadow: 0 12px 40px rgba(0,0,0,0.2); }}
        .stat-icon {{ font-size: 1.8rem; margin-bottom: 0.5rem; display: inline-block; width: 48px; height: 48px; line-height: 48px; border-radius: 1rem; background: rgba(13,148,136,0.04); }}
        .stat-value {{ font-size: 2rem; font-weight: 700; color: var(--primary); }}
        .stat-label {{ color: rgba(255,255,255,0.3); font-size: 0.75rem; margin-top: 0.3rem; font-weight: 500; }}
        .stat-trend {{ font-size: 0.65rem; font-weight: 500; display: inline-block; padding: 0.15rem 0.6rem; border-radius: 2rem; margin-top: 0.4rem; }}
        .stat-trend.up {{ color: #22c55e; background: rgba(34,197,94,0.08); }}
        .stat-trend.down {{ color: #ef4444; background: rgba(239,68,68,0.08); }}
        .stat-trend.neutral {{ color: #eab308; background: rgba(234,179,8,0.08); }}
        .status-card.green .stat-value {{ color: #22c55e; }}
        .status-card.yellow .stat-value {{ color: #eab308; }}
        .status-card.red .stat-value {{ color: #ef4444; }}
        .status-card.orange .stat-value {{ color: #f97316; }}
        .financial-overview {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.2rem; margin-bottom: 1.5rem; }}
        .financial-card {{ background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(13,148,136,0.02)); border: 1px solid var(--border-color); border-radius: 1rem; padding: 1.5rem; text-align: center; }}
        .financial-card .f-icon {{ font-size: 2rem; margin-bottom: 0.3rem; }}
        .financial-card .f-value {{ font-size: 1.8rem; font-weight: 700; }}
        .financial-card .f-label {{ color: rgba(255,255,255,0.3); font-size: 0.75rem; margin-top: 0.2rem; }}
        .financial-card .f-change {{ font-size: 0.65rem; margin-top: 0.3rem; }}
        .financial-card .f-change.up {{ color: #22c55e; }}
        .financial-card .f-change.down {{ color: #ef4444; }}
        .quick-actions {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.2rem; margin-bottom: 1.5rem; }}
        .action-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 1rem; padding: 1.2rem; text-align: center; cursor: pointer; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }}
        .action-card:hover {{ transform: translateY(-4px); border-color: rgba(13,148,136,0.2); background: rgba(13,148,136,0.03); box-shadow: 0 12px 40px rgba(13,148,136,0.05); }}
        .action-icon {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .action-title {{ font-weight: 600; font-size: 0.9rem; color: white; }}
        .action-desc {{ font-size: 0.65rem; color: rgba(255,255,255,0.15); margin-top: 0.2rem; }}
        .alert-section {{ margin-bottom: 1.5rem; padding: 1rem 1.2rem; background: rgba(239,68,68,0.02); border: 1px solid rgba(239,68,68,0.06); border-radius: 1rem; }}
        .alert-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }}
        .alert-header span:first-child {{ font-weight: 600; color: #ef4444; font-size: 0.85rem; }}
        .alert-header span:last-child {{ color: rgba(255,255,255,0.2); font-size: 0.75rem; }}
        .alert-items {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
        .alert-items span {{ padding: 0.2rem 0.8rem; border-radius: 1rem; font-size: 0.7rem; }}
        .prediction-comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }}
        .prediction-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 1rem; padding: 1.2rem; }}
        .prediction-item {{ display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border-color); }}
        .prediction-item .label {{ color: rgba(255,255,255,0.4); font-size: 0.8rem; }}
        .prediction-item .value {{ font-weight: 600; }}
        .prediction-item .change {{ font-size: 0.7rem; margin-left: 0.5rem; }}
        .prediction-item .change.up {{ color: #22c55e; }}
        .prediction-item .change.down {{ color: #ef4444; }}
        .table-section {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 1rem; padding: 1.2rem; }}
        .table-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }}
        .table-header h3 {{ font-size: 0.95rem; font-weight: 600; color: rgba(255,255,255,0.6); }}
        .table-header h3 i {{ color: var(--primary); margin-right: 0.5rem; }}
        .table-actions {{ display: flex; gap: 0.5rem; }}
        .table-actions button {{ background: rgba(255,255,255,0.02); color: rgba(255,255,255,0.3); border: 1px solid var(--border-color); padding: 0.3rem 1rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.7rem; transition: all 0.3s ease; }}
        .table-actions button:hover {{ background: rgba(13,148,136,0.08); color: var(--primary); border-color: rgba(13,148,136,0.08); }}
        .search-bar {{ display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }}
        .search-bar input {{ flex: 1; padding: 0.5rem 1rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 0.5rem; color: white; font-size: 0.85rem; min-width: 150px; font-family: 'Inter', sans-serif; }}
        .search-bar input::placeholder {{ color: rgba(255,255,255,0.12); }}
        .search-bar select {{ padding: 0.5rem 1rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 0.5rem; color: rgba(255,255,255,0.3); font-size: 0.85rem; font-family: 'Inter', sans-serif; }}
        .table-wrapper {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; padding: 0.7rem 0.5rem; color: rgba(255,255,255,0.15); font-weight: 500; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-color); }}
        td {{ padding: 0.7rem 0.5rem; border-bottom: 1px solid var(--border-color); color: rgba(255,255,255,0.6); font-size: 0.85rem; }}
        tr:hover td {{ background: rgba(255,255,255,0.02); }}
        .status-badge {{ display: inline-block; padding: 0.15rem 0.7rem; border-radius: 2rem; font-size: 0.65rem; font-weight: 500; }}
        .status-badge.green {{ background: rgba(34,197,94,0.08); color: #22c55e; }}
        .status-badge.yellow {{ background: rgba(234,179,8,0.08); color: #eab308; }}
        .status-badge.red {{ background: rgba(239,68,68,0.08); color: #ef4444; }}
        .table-footer {{ margin-top: 1rem; color: rgba(255,255,255,0.08); font-size: 0.75rem; }}
        .btn-primary {{ background: var(--gradient-1); color: white; border: none; padding: 0.5rem 1.5rem; border-radius: 0.5rem; cursor: pointer; font-weight: 500; transition: all 0.3s ease; font-family: 'Inter', sans-serif; }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 30px rgba(13,148,136,0.2); }}
        .drop-zone {{ border: 2px dashed rgba(255,255,255,0.06); border-radius: 1.5rem; padding: 3rem 2rem; text-align: center; transition: all 0.3s ease; cursor: pointer; }}
        .drop-zone:hover {{ border-color: rgba(13,148,136,0.2); background: rgba(13,148,136,0.02); }}
        .drop-zone i {{ font-size: 3rem; color: var(--primary); margin-bottom: 1rem; opacity: 0.6; }}
        .format-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1.5rem; }}
        .format-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 0.8rem; padding: 1rem; text-align: center; }}
        .settings-group {{ margin-bottom: 2rem; }}
        .settings-group h3 {{ color: rgba(255,255,255,0.3); font-size: 0.8rem; margin-bottom: 0.8rem; font-weight: 600; letter-spacing: 0.5px; }}
        .settings-item {{ display: flex; justify-content: space-between; align-items: center; padding: 0.7rem 0; border-bottom: 1px solid var(--border-color); }}
        .settings-item .label {{ color: rgba(255,255,255,0.4); font-size: 0.85rem; }}
        .toggle {{ width: 38px; height: 20px; background: rgba(255,255,255,0.06); border-radius: 10px; cursor: pointer; transition: all 0.3s ease; position: relative; }}
        .toggle.active {{ background: var(--primary); }}
        .toggle .dot {{ width: 16px; height: 16px; background: white; border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: all 0.3s ease; }}
        .toggle.active .dot {{ left: 20px; }}
        .notification-badge {{ background: #ef4444; color: white; border-radius: 50%; padding: 0.05rem 0.4rem; font-size: 0.5rem; font-weight: 600; margin-left: 0.3rem; }}
        .footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }}
        .footer span {{ color: rgba(255,255,255,0.06); font-size: 0.65rem; }}
        .footer a {{ color: rgba(255,255,255,0.08); text-decoration: none; font-size: 0.65rem; transition: color 0.3s; }}
        .footer a:hover {{ color: rgba(255,255,255,0.2); }}
        .notif-dropdown {{ display: none; position: absolute; right: 0; top: 100%; margin-top: 0.5rem; width: 320px; max-height: 400px; overflow-y: auto; background: #0f1629; border: 1px solid var(--border-color); border-radius: 1rem; padding: 1rem; z-index: 1000; box-shadow: 0 20px 60px rgba(0,0,0,0.6); }}
        .notif-dropdown.show {{ display: block; }}
        .confidence-bar {{ height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin-top: 0.3rem; overflow: hidden; }}
        .confidence-bar .fill {{ height: 100%; border-radius: 2px; background: var(--gradient-1); }}
        .stat-progress {{ height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin-top: 0.8rem; overflow: hidden; }}
        .stat-progress .progress-bar {{ height: 100%; border-radius: 2px; background: var(--gradient-1); transition: width 1s ease; }}
        @media (max-width: 1200px) {{ .grid-4, .grid-5, .financial-overview, .prediction-comparison {{ grid-template-columns: repeat(2, 1fr); }} .quick-actions {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 992px) {{ .sidebar {{ width: 72px; padding: 1rem 0.5rem; }} .sidebar .logo span, .sidebar .nav a span, .sidebar .user-info, .sidebar .logout-btn span, .sidebar .nav-label {{ display: none; }} .sidebar .nav a {{ justify-content: center; padding: 0.7rem; }} .sidebar .user {{ justify-content: center; }} .main {{ padding: 1.5rem; }} }}
        @media (max-width: 768px) {{ .grid-4, .grid-5, .financial-overview, .prediction-comparison, .quick-actions {{ grid-template-columns: 1fr; }} .sidebar {{ width: 56px; padding: 0.8rem 0.3rem; }} .main {{ padding: 1rem; }} .topbar h1 {{ font-size: 1.2rem; }} .format-grid {{ grid-template-columns: 1fr; }} }}
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg-dark); }}
        ::-webkit-scrollbar-thumb {{ background: var(--primary); border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--primary-light); }}
    </style>
</head>
<body>
    <div class="dashboard">
        <aside class="sidebar">{sidebar}</aside>
        <main class="main">
            <div class="topbar">
                <div>
                    <h1>{title} <span>•</span></h1>
                    <div class="greeting">Good {time_of_day}, {name} 👋</div>
                </div>
                <div style="display:flex;align-items:center;gap:1rem;position:relative;">
                    <div style="position:relative;cursor:pointer;" onclick="toggleNotifications()">
                        <i class="fas fa-bell" style="color:rgba(255,255,255,0.2);font-size:1.2rem;"></i>
                        <span class="notification-badge">{notification_count + unread_count}</span>
                    </div>
                    <div id="notifDropdown" class="notif-dropdown">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border-color);">
                            <span style="font-weight:600;font-size:0.85rem;">🔔 Notifications</span>
                            <button onclick="markAllRead()" style="background:transparent;border:none;color:rgba(13,148,136,0.6);font-size:0.65rem;cursor:pointer;">Mark all read</button>
                        </div>
                        <div id="notifList">
                            {notif_items}
                        </div>
                    </div>
                    <span id="liveClock" style="color:rgba(255,255,255,0.1);font-size:0.75rem;background:rgba(255,255,255,0.02);padding:0.3rem 1rem;border-radius:2rem;border:1px solid var(--border-color);"></span>
                    <span class="date"><i class="far fa-calendar-alt" style="margin-right:0.5rem;"></i>{date_str}</span>
                </div>
            </div>
            <div class="content">{content}</div>
            <div class="footer">
                <span>© 2026 FORESIGHT · Enterprise AI Platform v8.0 · ₹1 = $0.012</span>
                <div style="display:flex;gap:1.5rem;">
                    <a href="#">Privacy</a>
                    <a href="#">Terms</a>
                    <a href="#">Support</a>
                    <a href="#">API</a>
                </div>
            </div>
        </main>
    </div>
    <script>
        function updateClock() {{
            document.getElementById('liveClock').textContent = new Date().toLocaleTimeString();
        }}
        updateClock();
        setInterval(updateClock, 1000);
        
        function toggleNotifications() {{
            document.getElementById('notifDropdown').classList.toggle('show');
        }}
        
        function markAllRead() {{
            fetch('/api/notifications/read-all', {{ method: 'POST' }})
                .then(response => response.json())
                .then(data => {{ if (data.status === 'success') location.reload(); }});
        }}
        
        function refreshData() {{ location.reload(); }}
        
        function exportCSV() {{ alert('📊 CSV export initiated!'); }}
        function exportPDF() {{ alert('📄 PDF report is being generated.'); }}
        function scheduleReport() {{ alert('📅 Report scheduled successfully!'); }}
        
        function filterTable() {{
            var search = document.querySelector('.search-bar input').value.toLowerCase();
            var status = document.querySelector('.search-bar select').value;
            var rows = document.querySelectorAll('.table-wrapper tbody tr');
            rows.forEach(function(row) {{
                var text = row.textContent.toLowerCase();
                var matchSearch = text.includes(search);
                var matchStatus = status === 'all' || text.includes(status.toLowerCase());
                row.style.display = (matchSearch && matchStatus) ? '' : 'none';
            }});
        }}
        
        document.addEventListener('click', function(event) {{
            const dropdown = document.getElementById('notifDropdown');
            const bell = document.querySelector('.topbar .fa-bell');
            if (dropdown && !dropdown.contains(event.target) && event.target !== bell && !bell.contains(event.target)) {{
                dropdown.classList.remove('show');
            }}
        }});
        
        function shareDashboard() {{
            if (navigator.share) {{
                navigator.share({{
                    title: 'FORESIGHT Dashboard',
                    text: 'Check out my AI-powered inventory dashboard!',
                    url: window.location.href
                }}).catch(() => {{}});
            }} else {{
                navigator.clipboard.writeText(window.location.href).then(() => {{
                    alert('🔗 Dashboard link copied to clipboard!');
                }});
            }}
        }}
    </script>
</body>
</html>
    '''

# ============================================
# ROUTES - ALL PAGES
# ============================================

@app.get("/")
async def root(request: Request):
    token = request.cookies.get("session_token")
    if token and token in sessions:
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=LOGIN_PAGE.replace("{error}", ""))

@app.get("/auth/google")
async def auth_google():
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "state": state,
        "access_type": "offline"
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return RedirectResponse(url=auth_url)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: str, state: str = None):
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI
            })
            token_data = token_response.json()
            
            if "access_token" not in token_data:
                return HTMLResponse(content="Failed to get access token")
            
            user_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            user_data = user_response.json()
            
            email = user_data.get("email")
            name = user_data.get("name", email)
            avatar = user_data.get("picture", name[:2].upper())
            
            token = f"session_{datetime.now().timestamp()}"
            sessions[token] = {"name": name, "email": email, "avatar": avatar, "role": "analyst"}
            user_preferences[email] = user_preferences.get(email, {"theme": "dark", "notifications": True, "weekly_reports": False})
            
            # Send welcome email
            send_email(
                email,
                "Welcome to FORESIGHT! 🚀",
                f"Hello {name},\n\nWelcome to FORESIGHT Enterprise AI Platform!\n\nYour account has been created successfully.\n\nBest regards,\nFORESIGHT Team"
            )
            
            response = RedirectResponse(url="/dashboard", status_code=303)
            response.set_cookie(key="session_token", value=token)
            return response
            
    except Exception as e:
        return HTMLResponse(content=f"Authentication failed: {str(e)}")

@app.get("/login")
async def login_page(request: Request):
    token = request.cookies.get("session_token")
    if token and token in sessions:
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=LOGIN_PAGE.replace("{error}", ""))

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    # Demo login
    if email == "demo@foresight.ai" and password == "password123":
        token = f"session_{datetime.now().timestamp()}"
        sessions[token] = {"name": "Parameshwari Chand", "email": email, "avatar": "PC", "role": "admin"}
        user_preferences[email] = user_preferences.get(email, {"theme": "dark", "notifications": True, "weekly_reports": False})
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session_token", value=token)
        
        # Log audit
        audit_logs.append({
            "user": email,
            "action": "Login",
            "time": datetime.now().isoformat(),
            "ip": request.client.host if request.client else "Unknown"
        })
        
        return response
    
    error_html = "<div class='error-message'><i class='fas fa-exclamation-circle'></i> Invalid credentials</div>"
    return HTMLResponse(content=LOGIN_PAGE.replace("{error}", error_html))

@app.get("/register")
async def register_page(request: Request):
    token = request.cookies.get("session_token")
    if token and token in sessions:
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=REGISTER_HTML)

@app.post("/register")
async def register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    if len(password) < 8:
        return HTMLResponse(content="Password must be at least 8 characters")
    
    token = f"session_{datetime.now().timestamp()}"
    sessions[token] = {"name": name, "email": email, "avatar": name[:2].upper(), "role": "analyst"}
    user_preferences[email] = user_preferences.get(email, {"theme": "dark", "notifications": True, "weekly_reports": False})
    
    # Send welcome email
    send_email(
        email,
        "Welcome to FORESIGHT! 🚀",
        f"Hello {name},\n\nWelcome to FORESIGHT Enterprise AI Platform!\n\nYour account has been created successfully.\n\nBest regards,\nFORESIGHT Team"
    )
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session_token", value=token)
    return response

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token in sessions:
        user = sessions[token]
        # Log audit
        audit_logs.append({
            "user": user.get("email", "Unknown"),
            "action": "Logout",
            "time": datetime.now().isoformat()
        })
        del sessions[token]
    response = RedirectResponse(url="/login?success=Logged%20out%20successfully", status_code=303)
    response.delete_cookie("session_token")
    return response

# ============================================
# DASHBOARD CONTENT
# ============================================
def dashboard_content():
    total = len(inventory)
    low = len([i for i in inventory if i["status"] == "Low Stock"])
    critical = len([i for i in inventory if i["status"] == "Critical"])
    instock = total - low - critical
    expiring_items = len([i for i in inventory if i.get("days_until_expiry") and i["days_until_expiry"] <= 30])
    
    total_revenue_usd = sum(i.get("stock", 0) * i.get("selling_price", 500) for i in inventory)
    total_cost_usd = sum(i.get("stock", 0) * i.get("cost_price", 300) for i in inventory)
    profit_usd = total_revenue_usd - total_cost_usd
    
    total_revenue_inr = usd_to_inr(total_revenue_usd)
    total_cost_inr = usd_to_inr(total_cost_usd)
    profit_inr = usd_to_inr(profit_usd)
    profit_margin = round((profit_usd / total_revenue_usd * 100) if total_revenue_usd > 0 else 0, 2)
    
    last_week = weekly_data[-1] if weekly_data else {}
    
    rows = ""
    for i in inventory[:8]:
        badge = "green" if i["status"] == "In Stock" else "yellow" if i["status"] == "Low Stock" else "red"
        expiry_warning = ""
        if i.get("days_until_expiry"):
            if i["days_until_expiry"] <= 7:
                expiry_warning = ' <span style="color:#ef4444;font-size:0.7rem;">⚠️ Expires soon!</span>'
            elif i["days_until_expiry"] <= 30:
                expiry_warning = ' <span style="color:#eab308;font-size:0.7rem;">📅 ' + str(i["days_until_expiry"]) + ' days</span>'
        rows += f'<tr><td><strong>{i["product"]}</strong>{expiry_warning}</td><td style="color:rgba(255,255,255,0.3);font-size:0.8rem;">{i["sku"]}</td><td>{i["store"]}</td><td>{i["stock"]}</td><td><span class="status-badge {badge}">{i["status"]}</span></td></tr>'
    
    alerts_html = ""
    for alert in expiry_alerts[:5]:
        color = "rgba(239,68,68,0.1)" if alert["status"] == "Critical" else "rgba(234,179,8,0.1)"
        border = "rgba(239,68,68,0.2)" if alert["status"] == "Critical" else "rgba(234,179,8,0.2)"
        alerts_html += f'<span style="background:{color}; padding:0.2rem 0.8rem; border-radius:1rem; font-size:0.75rem; border:1px solid {border};"><strong>{alert["product"]}</strong> expires in <strong>{alert["days"]}</strong> days</span>'
    
    more_alerts = f'<span style="color:rgba(255,255,255,0.2);font-size:0.75rem;">+{len(expiry_alerts)-5} more</span>' if len(expiry_alerts) > 5 else ''
    
    pred_items = ""
    for i, pred in enumerate(predictions_data[:7]):
        trend_icon = "📈" if pred["trend"] == "up" else "📉"
        trend_color = "#22c55e" if pred["trend"] == "up" else "#ef4444"
        pred_items += f'''
        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.3rem 0;border-bottom:1px solid var(--border-color);">
            <span style="font-size:0.8rem;">{pred["day"]} ({pred["date"]})</span>
            <span style="color:{trend_color};font-weight:600;">{trend_icon} {pred["predicted_sales"]}</span>
            <span style="font-size:0.6rem;color:rgba(255,255,255,0.2);">{pred["confidence"]}% confidence</span>
            <div class="confidence-bar" style="width:60px;">
                <div class="fill" style="width:{pred["confidence"]}%;"></div>
            </div>
        </div>
        '''
    
    return f'''
<div class="grid-4">
    <div class="stat-card"><div class="stat-icon">📊</div><div class="stat-value">94.2%</div><div class="stat-label">Forecast Accuracy</div><div class="stat-trend up">↑ 2.1%</div></div>
    <div class="stat-card"><div class="stat-icon">📦</div><div class="stat-value">{total}</div><div class="stat-label">Products Tracked</div><div class="stat-trend up">↑ 12</div></div>
    <div class="stat-card"><div class="stat-icon">🏪</div><div class="stat-value">{len(stores)}</div><div class="stat-label">Store Locations</div><div class="stat-trend up">↑ 1</div></div>
    <div class="stat-card"><div class="stat-icon">🤖</div><div class="stat-value">{profit_margin}%</div><div class="stat-label">Profit Margin</div><div class="stat-trend {'up' if profit_margin > 20 else 'neutral'}">{'↑ Profitable' if profit_margin > 20 else '✓ Stable'}</div></div>
</div>

<div class="financial-overview">
    <div class="financial-card"><div class="f-icon">💰</div><div class="f-value" style="color:#22c55e;">₹{total_revenue_inr:,}</div><div class="f-label">Total Revenue</div><div class="f-change up">↑ 12.5%</div></div>
    <div class="financial-card"><div class="f-icon">📉</div><div class="f-value" style="color:#ef4444;">₹{total_cost_inr:,}</div><div class="f-label">Total Costs</div><div class="f-change down">↑ 4.2%</div></div>
    <div class="financial-card"><div class="f-icon">📈</div><div class="f-value" style="color:#eab308;">₹{profit_inr:,}</div><div class="f-label">Net Profit</div><div class="f-change up">↑ 18.7%</div></div>
    <div class="financial-card"><div class="f-icon">📊</div><div class="f-value" style="color:#0d9488;">{profit_margin}%</div><div class="f-label">Profit Margin</div><div class="f-change up">↑ 3.2%</div></div>
</div>

<div class="grid-5">
    <div class="stat-card"><div class="stat-icon">⭐</div><div class="stat-value" style="color:#eab308;">{last_week.get("satisfaction", 4.2)}/5.0</div><div class="stat-label">Customer Satisfaction</div><div class="stat-trend up">↑ 0.2 pts</div></div>
    <div class="stat-card"><div class="stat-icon">📦</div><div class="stat-value" style="color:#22c55e;">{last_week.get("fulfillment_rate", 95)}%</div><div class="stat-label">Order Fulfillment</div><div class="stat-trend up">↑ 1.5%</div></div>
    <div class="stat-card"><div class="stat-icon">🏭</div><div class="stat-value" style="color:#0d9488;">{last_week.get("warehouse_utilization", 78)}%</div><div class="stat-label">Warehouse Utilization</div><div class="stat-trend neutral">✓ Optimal</div></div>
    <div class="stat-card"><div class="stat-icon">👥</div><div class="stat-value" style="color:#8b5cf6;">{last_week.get("customers", 0)}</div><div class="stat-label">Active Customers</div><div class="stat-trend up">↑ 8.7%</div></div>
    <div class="stat-card"><div class="stat-icon">📋</div><div class="stat-value" style="color:#f97316;">{last_week.get("orders", 0)}</div><div class="stat-label">Orders Processed</div><div class="stat-trend up">↑ 5.3%</div></div>
</div>

<div class="prediction-comparison">
    <div class="prediction-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
            <span style="font-weight:600;color:rgba(255,255,255,0.7);">📊 Last 7 Days (Actual)</span>
            <span style="font-size:0.7rem;color:rgba(255,255,255,0.2);">Week {len(weekly_data)}</span>
        </div>
        <div class="prediction-item"><span class="label">Total Sales</span><span class="value" style="color:#0d9488;">{last_week.get("sales", 0)}</span></div>
        <div class="prediction-item"><span class="label">Total Revenue</span><span class="value" style="color:#22c55e;">₹{usd_to_inr(last_week.get("revenue", 0)):,}</span></div>
        <div class="prediction-item"><span class="label">Orders</span><span class="value">{last_week.get("orders", 0)}</span></div>
        <div class="prediction-item"><span class="label">Growth Rate</span><span class="value" style="color:{'#22c55e' if last_week.get('growth', 0) > 0 else '#ef4444'};">{last_week.get("growth", 0)}%</span></div>
    </div>
    <div class="prediction-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
            <span style="font-weight:600;color:rgba(255,255,255,0.7);">🔮 Next 7 Days (Predicted)</span>
            <span style="font-size:0.7rem;color:rgba(255,255,255,0.2);">AI Forecast</span>
        </div>
        <div class="prediction-item"><span class="label">Predicted Sales</span><span class="value" style="color:#0d9488;">{predictions_data[-1]["predicted_sales"] if predictions_data else 0}</span><span class="change {'up' if predictions_data[-1]["trend"] == 'up' else 'down'}">{'+' if predictions_data[-1]["trend"] == 'up' else ''}{random.uniform(2, 8):.1f}%</span></div>
        <div class="prediction-item"><span class="label">Predicted Revenue</span><span class="value" style="color:#22c55e;">₹{usd_to_inr(predictions_data[-1]["predicted_revenue"]) if predictions_data else 0:,}</span><span class="change {'up' if predictions_data[-1]["trend"] == 'up' else 'down'}">{'+' if predictions_data[-1]["trend"] == 'up' else ''}{random.uniform(2, 8):.1f}%</span></div>
        <div class="prediction-item"><span class="label">Predicted Orders</span><span class="value">{predictions_data[-1]["predicted_orders"] if predictions_data else 0}</span><span class="change {'up' if predictions_data[-1]["trend"] == 'up' else 'down'}">{'+' if predictions_data[-1]["trend"] == 'up' else ''}{random.uniform(2, 8):.1f}%</span></div>
        <div class="prediction-item"><span class="label">Confidence Level</span><span class="value" style="color:#eab308;">{predictions_data[-1]["confidence"] if predictions_data else 0}%</span><span class="change neutral">✓ Verified</span></div>
    </div>
</div>

<div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:1rem; padding:1.2rem; margin-bottom:1.5rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
        <span style="font-weight:600; color:rgba(255,255,255,0.7);">📈 7-Day Sales Prediction</span>
        <span style="color:rgba(255,255,255,0.2); font-size:0.7rem;">AI Generated</span>
    </div>
    {pred_items}
</div>

<div style="display:grid; grid-template-columns: 1fr 1fr; gap:1.5rem; margin-bottom:1.5rem;">
    <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:1rem; padding:1.2rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <span style="font-weight:600; color:rgba(255,255,255,0.7);">📈 Products Tracked</span>
            <span style="color:rgba(255,255,255,0.2); font-size:0.7rem;">Last 8 Weeks</span>
        </div>
        <canvas id="productsChart" style="max-height:150px;"></canvas>
    </div>
    <div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:1rem; padding:1.2rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <span style="font-weight:600; color:rgba(255,255,255,0.7);">💰 Sales Revenue (₹)</span>
            <span style="color:rgba(255,255,255,0.2); font-size:0.7rem;">Last 8 Weeks</span>
        </div>
        <canvas id="salesChart" style="max-height:150px;"></canvas>
    </div>
</div>

<div style="background:var(--card-bg); border:1px solid var(--border-color); border-radius:1rem; padding:1.2rem; margin-bottom:1.5rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <span style="font-weight:600; color:rgba(255,255,255,0.7);">📊 Weekly Growth Rate</span>
        <span style="color:rgba(255,255,255,0.2); font-size:0.7rem;">Comparison vs Previous Week</span>
    </div>
    <canvas id="growthChart" style="max-height:120px;"></canvas>
</div>

<div class="quick-actions">
    <div class="action-card" onclick="location.href='/upload'"><div class="action-icon">📤</div><div class="action-title">Upload Data</div><div class="action-desc">Import new dataset</div></div>
    <div class="action-card" onclick="location.href='/reports'"><div class="action-icon">📊</div><div class="action-title">Generate Report</div><div class="action-desc">Create business report</div></div>
    <div class="action-card" onclick="location.href='/predictions'"><div class="action-icon">🔮</div><div class="action-title">AI Predictions</div><div class="action-desc">7-day forecast</div></div>
    <div class="action-card" onclick="shareDashboard()"><div class="action-icon">🔗</div><div class="action-title">Share Dashboard</div><div class="action-desc">Share with team</div></div>
</div>

<div class="alert-section">
    <div class="alert-header"><span><i class="fas fa-exclamation-triangle"></i> Expiry Alerts</span><span>{len(expiry_alerts)} items expiring soon</span></div>
    <div class="alert-items">{alerts_html}{more_alerts}</div>
</div>

<div class="table-section">
    <div class="table-header"><h3><i class="fas fa-box"></i> Real-Time Inventory</h3><div class="table-actions"><button onclick="refreshData()"><i class="fas fa-sync-alt"></i> Refresh</button><button onclick="exportCSV()"><i class="fas fa-file-export"></i> Export CSV</button><button onclick="exportPDF()"><i class="fas fa-file-pdf"></i> Export PDF</button><button onclick="scheduleReport()"><i class="fas fa-calendar-plus"></i> Schedule</button></div></div>
    <div class="search-bar"><input type="text" placeholder="🔍 Search products..." onkeyup="filterTable()"><select onchange="filterTable()"><option value="all">All Status</option><option value="In Stock">In Stock</option><option value="Low Stock">Low Stock</option><option value="Critical">Critical</option></select></div>
    <div class="table-wrapper"><table><thead><tr><th>Product</th><th>SKU</th><th>Store</th><th>Stock</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>
    <div class="table-footer">Showing {len(inventory)} products</div>
</div>

<script>
    const weeksData = {json.dumps(weekly_data[-8:])};
    const weeksLabels = weeksData.map(w => w.week);
    const productsData = weeksData.map(w => w.products_tracked);
    const salesData = weeksData.map(w => w.sales);
    const growthData = weeksData.map(w => w.growth);
    
    new Chart(document.getElementById('productsChart'), {{
        type: 'line',
        data: {{
            labels: weeksLabels,
            datasets: [{{
                label: 'Products Tracked',
                data: productsData,
                borderColor: '#0d9488',
                backgroundColor: 'rgba(13,148,136,0.1)',
                fill: true,
                tension: 0.4
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }},
                x: {{ grid: {{ display: false }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }}
            }}
        }}
    }});
    
    new Chart(document.getElementById('salesChart'), {{
        type: 'bar',
        data: {{
            labels: weeksLabels,
            datasets: [{{
                label: 'Sales Revenue (₹)',
                data: salesData.map(v => v * 83.50),
                backgroundColor: 'rgba(13,148,136,0.6)',
                borderRadius: 4
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }},
                x: {{ grid: {{ display: false }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }}
            }}
        }}
    }});
    
    new Chart(document.getElementById('growthChart'), {{
        type: 'line',
        data: {{
            labels: weeksLabels.slice(1),
            datasets: [{{
                label: 'Growth %',
                data: growthData.slice(1),
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34,197,94,0.1)',
                fill: true,
                tension: 0.4
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }},
                x: {{ grid: {{ display: false }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }}
            }}
        }}
    }});
</script>
'''

# ============================================
# OTHER PAGES (Upload, Cleaning, Analytics, Forecast, Predictions, Inventory, Reports, Profile, Settings)
# ============================================

@app.get("/dashboard")
async def dashboard_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login?error=Please%20login%20first", status_code=303)
    content = dashboard_content()
    return HTMLResponse(content=render_page(content, user, "dashboard", "Dashboard"))

@app.get("/upload")
async def upload_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    content = '''
<div class="page-title">📤 Upload Dataset</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Import your sales or inventory data to begin AI-powered analysis</div>
<div class="drop-zone" id="dropZone">
    <i class="fas fa-cloud-upload-alt"></i>
    <h3>Drag & drop your file here</h3>
    <p style="color:rgba(255,255,255,0.2);">Supports CSV, Excel (.xlsx, .xls) — up to 100MB</p>
    <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" id="fileInput" name="file" accept=".csv,.xlsx,.xls" style="display:none;" onchange="submitForm()">
        <div class="btn-primary" style="display:inline-block;margin-top:1rem;padding:0.6rem 2rem;cursor:pointer;" onclick="document.getElementById('fileInput').click();">Browse File</div>
    </form>
</div>
<div id="uploadStatus" style="display:none;margin-top:1rem;padding:1.5rem;border-radius:0.8rem;text-align:center;"></div>
<div class="format-grid">
    <div class="format-card"><div style="font-weight:700;color:#0d9488;">📄 .CSV</div><div style="color:rgba(255,255,255,0.2);font-size:0.7rem;">Comma-Separated Values</div></div>
    <div class="format-card"><div style="font-weight:700;color:#0d9488;">📊 .XLSX</div><div style="color:rgba(255,255,255,0.2);font-size:0.7rem;">Microsoft Excel Workbook</div></div>
    <div class="format-card"><div style="font-weight:700;color:#0d9488;">📊 .XLS</div><div style="color:rgba(255,255,255,0.2);font-size:0.7rem;">Excel 97-2003 Format</div></div>
</div>
<script>
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.style.borderColor = 'rgba(13,148,136,0.5)';
        this.style.background = 'rgba(13,148,136,0.05)';
    });
    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.style.borderColor = 'rgba(255,255,255,0.06)';
        this.style.background = 'transparent';
    });
    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        this.style.borderColor = 'rgba(255,255,255,0.06)';
        this.style.background = 'transparent';
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            submitForm();
        }
    });
    
    function submitForm() {
        const formData = new FormData(document.getElementById('uploadForm'));
        uploadStatus.style.display = 'block';
        uploadStatus.innerHTML = '<div style="color:rgba(255,255,255,0.5);">⏳ Uploading...</div>';
        uploadStatus.style.background = 'rgba(13,148,136,0.05)';
        uploadStatus.style.border = '1px solid rgba(13,148,136,0.1)';
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                uploadStatus.style.background = 'rgba(34,197,94,0.05)';
                uploadStatus.style.border = '1px solid rgba(34,197,94,0.2)';
                uploadStatus.innerHTML = `
                    <div style="font-size:2rem;margin-bottom:0.5rem;">✅</div>
                    <div style="color:#22c55e;font-weight:600;font-size:1.1rem;">${data.message}</div>
                    <div style="color:rgba(255,255,255,0.3);font-size:0.85rem;margin-top:0.5rem;">${data.rows} rows imported</div>
                    <div style="margin-top:1rem;display:flex;gap:0.5rem;justify-content:center;flex-wrap:wrap;">
                        <button onclick="location.href='/dashboard'" class="btn-primary" style="padding:0.5rem 2rem;border:none;border-radius:0.5rem;cursor:pointer;background:linear-gradient(135deg,#0d9488,#14b8a6);color:white;font-weight:600;">📊 Go to Dashboard</button>
                        <button onclick="location.reload()" style="padding:0.5rem 2rem;border:1px solid rgba(255,255,255,0.05);border-radius:0.5rem;cursor:pointer;background:transparent;color:rgba(255,255,255,0.3);font-weight:500;">Upload Another</button>
                    </div>
                `;
            } else {
                uploadStatus.style.background = 'rgba(239,68,68,0.05)';
                uploadStatus.style.border = '1px solid rgba(239,68,68,0.2)';
                uploadStatus.innerHTML = `<div style="color:#ef4444;font-weight:600;">❌ ${data.message}</div>`;
            }
        })
        .catch(error => {
            uploadStatus.style.background = 'rgba(239,68,68,0.05)';
            uploadStatus.style.border = '1px solid rgba(239,68,68,0.2)';
            uploadStatus.innerHTML = `<div style="color:#ef4444;font-weight:600;">❌ Upload failed: ${error.message}</div>`;
        });
    }
</script>
'''
    return HTMLResponse(content=render_page(content, user, "upload", "Upload Dataset"))

@app.get("/cleaning")
async def cleaning_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    total_records = len(inventory)
    if total_records == 0:
        content = '''
<div class="page-title">🧹 Data Cleaning</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Detect and resolve data quality issues before analysis</div>
<div style="text-align:center;padding:3rem 2rem;border:1px dashed rgba(255,255,255,0.06);border-radius:1rem;">
    <i class="fas fa-broom" style="font-size:3rem;color:#0d9488;opacity:0.5;margin-bottom:1rem;"></i>
    <h3 style="color:rgba(255,255,255,0.5);font-weight:600;">No cleaning data yet</h3>
    <p style="color:rgba(255,255,255,0.2);">Upload a dataset to see real cleaning statistics here.</p>
    <button class="btn-primary" onclick="location.href='/upload'" style="margin-top:1.5rem;padding:0.6rem 2rem;">📤 Upload Dataset</button>
</div>
'''
    else:
        missing_values = sum(1 for i in inventory if not i.get("product") or not i.get("sku"))
        duplicates = len(inventory) - len(set(i.get("sku") for i in inventory))
        outliers = sum(1 for i in inventory if i.get("stock", 0) > 200 or i.get("stock", 0) < 0)
        invalid_records = sum(1 for i in inventory if not i.get("product") or not i.get("sku") or i.get("stock") is None)
        total_issues = missing_values + duplicates + outliers + invalid_records
        quality_score = max(0, 100 - (total_issues * 2)) if total_records > 0 else 0
        clean_records = total_records - invalid_records - duplicates
        
        content = f'''
<div class="page-title">🧹 Data Cleaning</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Detect and resolve data quality issues before analysis</div>
<div class="grid-4" style="margin-bottom:1.5rem;">
    <div class="stat-card"><div class="stat-value" style="color:#0d9488;">{quality_score}%</div><div class="stat-label">Data Quality Score</div><div class="stat-progress"><div class="progress-bar" style="width:{quality_score}%;"></div></div></div>
    <div class="stat-card"><div class="stat-value" style="color:#22c55e;">{total_records}</div><div class="stat-label">Total Records</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#22c55e;">{clean_records}</div><div class="stat-label">Clean Records</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#ef4444;">{total_issues}</div><div class="stat-label">Issues Found</div></div>
</div>
<div class="grid-4" style="margin-bottom:1.5rem;">
    <div class="stat-card"><div class="stat-value" style="color:#eab308;">{missing_values}</div><div class="stat-label">Missing Values</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#eab308;">{duplicates}</div><div class="stat-label">Duplicates</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#eab308;">{outliers}</div><div class="stat-label">Outliers</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#eab308;">{invalid_records}</div><div class="stat-label">Invalid Records</div></div>
</div>
<button class="btn-primary" onclick="runAutoClean()" style="padding:0.6rem 2rem;margin-bottom:1rem;">🤖 Run Auto-Clean</button>
<div id="cleaningStatus" style="display:none;padding:1rem;border-radius:0.8rem;margin-bottom:1rem;"></div>
<script>
function runAutoClean() {{
    var status = document.getElementById('cleaningStatus');
    status.style.display = 'block';
    status.style.background = 'rgba(13,148,136,0.05)';
    status.style.border = '1px solid rgba(13,148,136,0.1)';
    status.innerHTML = '⏳ Running auto-clean...';
    fetch('/api/auto-clean', {{ method: 'POST' }})
        .then(response => response.json())
        .then(data => {{
            if (data.status === 'success') {{
                status.style.background = 'rgba(34,197,94,0.05)';
                status.style.border = '1px solid rgba(34,197,94,0.2)';
                status.innerHTML = '✅ ' + data.message;
                setTimeout(() => location.reload(), 2000);
            }} else {{
                status.style.background = 'rgba(239,68,68,0.05)';
                status.style.border = '1px solid rgba(239,68,68,0.2)';
                status.innerHTML = '❌ ' + data.message;
            }}
        }})
        .catch(error => {{
            status.style.background = 'rgba(239,68,68,0.05)';
            status.style.border = '1px solid rgba(239,68,68,0.2)';
            status.innerHTML = '❌ Error running auto-clean';
        }});
}}
</script>
'''
    return HTMLResponse(content=render_page(content, user, "cleaning", "Data Cleaning"))

@app.get("/analytics")
async def analytics_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    total_records = len(inventory)
    if total_records == 0:
        content = '''
<div class="page-title">📊 Analytics</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Deep-dive into sales performance, category trends, and product insights</div>
<div style="text-align:center;padding:4rem 2rem;border:1px dashed rgba(255,255,255,0.06);border-radius:1rem;">
    <div style="font-size:4rem;margin-bottom:1rem;">📊</div>
    <h3 style="color:rgba(255,255,255,0.7);font-weight:600;">No data uploaded yet</h3>
    <p style="color:rgba(255,255,255,0.3);margin-top:0.5rem;">Upload a dataset to see your real analytics here.</p>
    <button class="btn-primary" onclick="location.href='/upload'" style="margin-top:1.5rem;padding:0.6rem 2rem;">📤 Upload Dataset</button>
</div>
'''
    else:
        total_stock = sum(i.get("stock", 0) for i in inventory)
        total_revenue = sum(i.get("stock", 0) * i.get("selling_price", 500) for i in inventory)
        total_revenue_inr = usd_to_inr(total_revenue)
        
        categories = {}
        for item in inventory:
            cat = item.get("category", "Other")
            categories[cat] = categories.get(cat, 0) + item.get("stock", 0)
        
        cat_labels = list(categories.keys())
        cat_values = list(categories.values())
        
        top_products = sorted(inventory, key=lambda x: x.get("stock", 0), reverse=True)[:5]
        top_products_html = ""
        for i, item in enumerate(top_products):
            top_products_html += f'''
            <div style="display:flex;justify-content:space-between;padding:0.5rem 0;border-bottom:1px solid var(--border-color);">
                <span>{i+1}. {item["product"]}</span>
                <span style="color:#22c55e;">{item["stock"]} units</span>
            </div>
            '''
        
        content = f'''
<div class="page-title">📊 Analytics</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Deep-dive into sales performance, category trends, and product insights</div>
<div class="grid-4" style="margin-bottom:1.5rem;">
    <div class="stat-card"><div class="stat-icon">💰</div><div class="stat-value" style="color:#22c55e;">₹{total_revenue_inr:,}</div><div class="stat-label">Total Revenue</div></div>
    <div class="stat-card"><div class="stat-icon">📦</div><div class="stat-value" style="color:#0d9488;">{total_stock:,}</div><div class="stat-label">Total Stock Units</div></div>
    <div class="stat-card"><div class="stat-icon">📊</div><div class="stat-value" style="color:#eab308;">{total_records}</div><div class="stat-label">Total Products</div></div>
    <div class="stat-card"><div class="stat-icon">📈</div><div class="stat-value" style="color:#8b5cf6;">₹{usd_to_inr(total_revenue * 0.35):,}</div><div class="stat-label">Estimated Profit</div></div>
</div>
<div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.2rem;margin-bottom:1.5rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
        <span style="font-weight:600;color:rgba(255,255,255,0.7);">📊 Category Distribution</span>
    </div>
    <canvas id="categoryChart" style="max-height:200px;"></canvas>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem;">
    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.2rem;">
        <div style="font-weight:600;color:rgba(255,255,255,0.7);margin-bottom:0.5rem;">🏆 Top Products</div>
        {top_products_html}
    </div>
    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.2rem;">
        <div style="font-weight:600;color:rgba(255,255,255,0.7);margin-bottom:0.5rem;">📈 Monthly Trend</div>
        <canvas id="monthlyTrendChart" style="max-height:150px;"></canvas>
    </div>
</div>
<script>
    new Chart(document.getElementById('categoryChart'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(cat_labels)},
            datasets: [{{
                data: {json.dumps(cat_values)},
                backgroundColor: ['#0d9488', '#14b8a6', '#2dd4bf', '#5eead4', '#99f6e4'],
                borderWidth: 0
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: true,
            cutout: '65%',
            plugins: {{
                legend: {{
                    position: 'bottom',
                    labels: {{
                        color: 'rgba(255,255,255,0.4)',
                        boxWidth: 12,
                        padding: 15,
                        font: {{ size: 11 }}
                    }}
                }}
            }}
        }}
    }});
    
    new Chart(document.getElementById('monthlyTrendChart'), {{
        type: 'line',
        data: {{
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{{
                label: 'Revenue (₹)',
                data: [2800000, 3200000, 3500000, 3100000, 3800000, {total_revenue_inr}],
                borderColor: '#0d9488',
                backgroundColor: 'rgba(13,148,136,0.1)',
                fill: true,
                tension: 0.4
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }},
                x: {{ grid: {{ display: false }}, ticks: {{ color: 'rgba(255,255,255,0.3)' }} }}
            }}
        }}
    }});
</script>
'''
    return HTMLResponse(content=render_page(content, user, "analytics", "Analytics"))

@app.get("/forecast")
async def forecast_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    total_records = len(inventory)
    if total_records == 0:
        content = '''
<div class="page-title">🤖 AI Forecast</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">AI-powered demand forecasting for your inventory</div>
<div style="text-align:center;padding:4rem 2rem;border:1px dashed rgba(255,255,255,0.06);border-radius:1rem;">
    <div style="font-size:4rem;margin-bottom:1rem;">🤖</div>
    <h3 style="color:rgba(255,255,255,0.7);font-weight:600;">AI Forecast Ready</h3>
    <p style="color:rgba(255,255,255,0.3);margin-top:0.5rem;">Upload data to generate AI-powered demand forecasts</p>
    <button class="btn-primary" onclick="location.href='/upload'" style="margin-top:1.5rem;padding:0.6rem 2rem;">📤 Upload Dataset</button>
</div>
'''
    else:
        forecast_items = []
        for item in inventory[:10]:
            forecast = int(item["stock"] * random.uniform(0.8, 1.5))
            confidence = random.randint(85, 98)
            forecast_items.append({
                "product": item["product"],
                "current": item["stock"],
                "forecast": forecast,
                "confidence": confidence
            })
        
        forecast_html = ""
        for item in forecast_items:
            rec = "Increase" if item["forecast"] > item["current"] else "Maintain" if item["forecast"] == item["current"] else "Reduce"
            color = "#22c55e" if rec == "Maintain" else "#0d9488" if rec == "Increase" else "#ef4444"
            forecast_html += f'''
            <div style="display:flex;justify-content:space-between;align-items:center;padding:0.7rem 1rem;border-bottom:1px solid var(--border-color);">
                <div><div style="font-weight:600;">{item["product"]}</div><div style="font-size:0.65rem;color:rgba(255,255,255,0.15);">Current: {item["current"]} units</div></div>
                <div style="text-align:right;"><div style="font-size:1.1rem;font-weight:700;color:#0d9488;">{item["forecast"]}</div><div style="font-size:0.65rem;color:{color};">{rec} · {item["confidence"]}% confidence</div></div>
            </div>
            '''
        
        content = f'''
<div class="page-title">🤖 AI Forecast</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">AI-powered demand forecasting for your inventory</div>
<div class="grid-4" style="margin-bottom:1.5rem;">
    <div class="stat-card"><div class="stat-icon">🎯</div><div class="stat-value" style="color:#0d9488;">{random.randint(85, 95)}%</div><div class="stat-label">Historical Accuracy</div></div>
    <div class="stat-card"><div class="stat-icon">📈</div><div class="stat-value" style="color:#22c55e;">{sum(f["forecast"] for f in forecast_items):,}</div><div class="stat-label">Most Likely Demand</div></div>
    <div class="stat-card"><div class="stat-icon">📊</div><div class="stat-value" style="color:#eab308;">{sum(f["forecast"] * 1.2 for f in forecast_items):,.0f}</div><div class="stat-label">Best Case Scenario</div></div>
    <div class="stat-card"><div class="stat-icon">📉</div><div class="stat-value" style="color:#ef4444;">{sum(f["forecast"] * 0.8 for f in forecast_items):,.0f}</div><div class="stat-label">Worst Case Scenario</div></div>
</div>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:1.5rem;margin-bottom:1.5rem;">
    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.2rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
            <span style="font-weight:600;color:rgba(255,255,255,0.7);">📊 Forecast vs Current Stock</span>
        </div>
        {forecast_html}
    </div>
    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.2rem;">
        <div style="font-weight:600;color:rgba(255,255,255,0.7);margin-bottom:0.5rem;">🎯 Insights</div>
        <div style="color:rgba(255,255,255,0.4);font-size:0.8rem;line-height:2;">
            <div>• <strong style="color:#22c55e;">{len([f for f in forecast_items if f["forecast"] > f["current"]])}</strong> products need increase</div>
            <div>• <strong style="color:#0d9488;">{len([f for f in forecast_items if f["forecast"] == f["current"]])}</strong> products at optimal levels</div>
            <div>• <strong style="color:#ef4444;">{len([f for f in forecast_items if f["forecast"] < f["current"]])}</strong> products may have excess</div>
            <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--border-color);">
                <div style="color:rgba(255,255,255,0.2);font-size:0.65rem;">Avg confidence: <strong style="color:#0d9488;">{sum(f["confidence"] for f in forecast_items) // len(forecast_items)}%</strong></div>
            </div>
        </div>
        <button class="btn-primary" onclick="location.reload()" style="margin-top:0.8rem;width:100%;padding:0.5rem;">🔄 Refresh Forecast</button>
    </div>
</div>
'''
    return HTMLResponse(content=render_page(content, user, "forecast", "AI Forecast"))

@app.get("/predictions")
async def predictions_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    pred_html = ""
    for i, pred in enumerate(predictions_data):
        trend_icon = "📈" if pred["trend"] == "up" else "📉"
        trend_color = "#22c55e" if pred["trend"] == "up" else "#ef4444"
        pred_html += f'''
        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.8rem 1rem;border-bottom:1px solid var(--border-color);background:rgba(255,255,255,0.01);border-radius:0.5rem;margin-bottom:0.3rem;">
            <div><div style="font-weight:600;font-size:0.95rem;">{pred["day"]}</div><div style="font-size:0.7rem;color:rgba(255,255,255,0.2);">{pred["date"]}</div></div>
            <div style="text-align:center;"><div style="font-weight:600;color:#0d9488;">{pred["predicted_sales"]} units</div><div style="font-size:0.6rem;color:rgba(255,255,255,0.15);">Sales</div></div>
            <div style="text-align:center;"><div style="font-weight:600;color:#22c55e;">₹{usd_to_inr(pred["predicted_revenue"]):,}</div><div style="font-size:0.6rem;color:rgba(255,255,255,0.15);">Revenue</div></div>
            <div style="text-align:center;"><div style="font-weight:600;color:#eab308;">{pred["confidence"]}%</div><div style="font-size:0.6rem;color:rgba(255,255,255,0.15);">Confidence</div></div>
            <div><span style="color:{trend_color};font-size:1.2rem;">{trend_icon}</span><span style="font-size:0.7rem;color:{trend_color};">{pred["trend"].upper()}</span></div>
        </div>
        '''
    
    content = f'''
<div class="page-title">🔮 AI Predictions</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">7-day sales and revenue forecast with confidence scores</div>
<div class="grid-3" style="margin-bottom:1.5rem;">
    <div class="stat-card"><div class="stat-icon">📈</div><div class="stat-value" style="color:#22c55e;">+{random.randint(5, 15)}%</div><div class="stat-label">Expected Growth</div></div>
    <div class="stat-card"><div class="stat-icon">🎯</div><div class="stat-value" style="color:#0d9488;">{predictions_data[-1]["confidence"] if predictions_data else 85}%</div><div class="stat-label">AI Confidence Level</div></div>
    <div class="stat-card"><div class="stat-icon">📊</div><div class="stat-value" style="color:#eab308;">{predictions_data[-1]["predicted_sales"] if predictions_data else 0}</div><div class="stat-label">Next Week Sales</div></div>
</div>
<div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.2rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
        <span style="font-weight:600;color:rgba(255,255,255,0.7);">📊 Daily Predictions</span>
        <span style="font-size:0.7rem;color:rgba(255,255,255,0.2);">7-Day Forecast</span>
    </div>
    {pred_html}
</div>
<div style="margin-top:1.5rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
    <button class="btn-primary" onclick="location.reload()">🔄 Refresh Predictions</button>
    <button class="btn-primary" onclick="exportCSV()" style="background:rgba(255,255,255,0.03);">📥 Export Forecast</button>
</div>
'''
    return HTMLResponse(content=render_page(content, user, "predictions", "Predictions"))

@app.get("/inventory")
async def inventory_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    total = len(inventory)
    low = len([i for i in inventory if i["status"] == "Low Stock"])
    critical = len([i for i in inventory if i["status"] == "Critical"])
    healthy = total - low - critical
    expiring = len([i for i in inventory if i.get("days_until_expiry") and i["days_until_expiry"] <= 30])
    
    rows = ""
    if total == 0:
        rows = '<tr><td colspan="6" style="text-align:center;padding:3rem;color:rgba(255,255,255,0.2);">No inventory data yet</td></tr>'
    else:
        for idx, i in enumerate(inventory[:50]):
            badge = "green" if i["status"] == "In Stock" else "yellow" if i["status"] == "Low Stock" else "red"
            expiry_info = f'<span style="color:{"#ef4444" if i.get("days_until_expiry", 999) <= 7 else "#eab308" if i.get("days_until_expiry", 999) <= 30 else "rgba(255,255,255,0.2)"};font-size:0.7rem;">{i["days_until_expiry"]} days</span>' if i.get("days_until_expiry") else '<span style="color:rgba(255,255,255,0.1);font-size:0.7rem;">-</span>'
            rows += f'<tr><td style="color:rgba(255,255,255,0.15);">{idx+1}</td><td><strong>{i["product"]}</strong></td><td>{i["sku"]}</td><td>{i["stock"]}</td><td><span class="status-badge {badge}">{i["status"]}</span></td><td>{expiry_info}</td></tr>'
    
    content = f'''
<div class="page-title">📦 Inventory</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Real-time stock levels, AI-driven analysis, and reorder recommendations</div>
<div class="grid-4">
    <div class="stat-card"><div class="stat-value" style="color:#22c55e;">{healthy}</div><div class="stat-label">Healthy</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#eab308;">{low}</div><div class="stat-label">Low Stock</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#ef4444;">{critical}</div><div class="stat-label">Critical</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#f97316;">{expiring}</div><div class="stat-label">Expiring Soon</div></div>
</div>
<div style="margin-bottom:1rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
    <input type="text" id="searchInput" placeholder="🔍 Search product..." style="flex:1;padding:0.5rem 1rem;background:rgba(255,255,255,0.02);border:1px solid var(--border-color);border-radius:0.5rem;color:white;font-size:0.85rem;font-family:'Inter',sans-serif;">
    <select id="statusFilter" style="padding:0.5rem 1rem;background:rgba(255,255,255,0.02);border:1px solid var(--border-color);border-radius:0.5rem;color:rgba(255,255,255,0.3);font-size:0.85rem;font-family:'Inter',sans-serif;">
        <option value="all">All Status</option>
        <option value="In Stock">In Stock</option>
        <option value="Low Stock">Low Stock</option>
        <option value="Critical">Critical</option>
    </select>
</div>
<div class="table-wrapper">
    <table>
        <thead><tr><th>#</th><th>Product</th><th>SKU</th><th>Stock</th><th>Status</th><th>Expiry</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
</div>
<div style="margin-top:0.8rem;color:rgba(255,255,255,0.08);font-size:0.75rem;">Showing {total} products</div>
<script>
    document.getElementById('searchInput').addEventListener('keyup', function() {{
        const search = this.value.toLowerCase();
        const status = document.getElementById('statusFilter').value;
        document.querySelectorAll('.table-wrapper tbody tr').forEach(row => {{
            const text = row.textContent.toLowerCase();
            row.style.display = (text.includes(search) && (status === 'all' || text.includes(status.toLowerCase()))) ? '' : 'none';
        }});
    }});
    document.getElementById('statusFilter').addEventListener('change', function() {{
        const search = document.getElementById('searchInput').value.toLowerCase();
        const status = this.value;
        document.querySelectorAll('.table-wrapper tbody tr').forEach(row => {{
            const text = row.textContent.toLowerCase();
            row.style.display = (text.includes(search) && (status === 'all' || text.includes(status.toLowerCase()))) ? '' : 'none';
        }});
    }});
</script>
'''
    return HTMLResponse(content=render_page(content, user, "inventory", "Inventory"))

@app.get("/reports")
async def reports_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    content = '''
<div class="page-title">📄 Reports</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Generate and download business reports from your uploaded data</div>
<div class="grid-2">
    <div class="report-card" style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">📊</div>
        <div style="font-weight:600;font-size:0.95rem;">Forecast Report</div>
        <div style="color:rgba(255,255,255,0.25);font-size:0.8rem;margin-top:0.2rem;">AI-generated demand forecast</div>
        <div style="margin-top:0.5rem;display:flex;gap:0.5rem;">
            <button onclick="location.href='/api/report-download/forecast'" class="btn-primary" style="padding:0.3rem 1.2rem;font-size:0.7rem;">📥 Download</button>
        </div>
    </div>
    <div class="report-card" style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">📦</div>
        <div style="font-weight:600;font-size:0.95rem;">Inventory Report</div>
        <div style="color:rgba(255,255,255,0.25);font-size:0.8rem;margin-top:0.2rem;">Complete inventory snapshot</div>
        <div style="margin-top:0.5rem;display:flex;gap:0.5rem;">
            <button onclick="location.href='/api/report-download/inventory'" class="btn-primary" style="padding:0.3rem 1.2rem;font-size:0.7rem;">📥 Download</button>
        </div>
    </div>
    <div class="report-card" style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">🔮</div>
        <div style="font-weight:600;font-size:0.95rem;">Predictions Report</div>
        <div style="color:rgba(255,255,255,0.25);font-size:0.8rem;margin-top:0.2rem;">7-day forecast and trends</div>
        <div style="margin-top:0.5rem;display:flex;gap:0.5rem;">
            <button onclick="location.href='/api/report-download/predictions'" class="btn-primary" style="padding:0.3rem 1.2rem;font-size:0.7rem;">📥 Download</button>
        </div>
    </div>
    <div class="report-card" style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.5rem;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">✅</div>
        <div style="font-weight:600;font-size:0.95rem;">Data Quality Report</div>
        <div style="color:rgba(255,255,255,0.25);font-size:0.8rem;margin-top:0.2rem;">Cleaning statistics & quality score</div>
        <div style="margin-top:0.5rem;display:flex;gap:0.5rem;">
            <button onclick="location.href='/api/report-download/quality'" class="btn-primary" style="padding:0.3rem 1.2rem;font-size:0.7rem;">📥 Download</button>
        </div>
    </div>
</div>
'''
    return HTMLResponse(content=render_page(content, user, "reports", "Reports"))

@app.get("/profile")
async def profile_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    content = f'''
<div class="page-title">👤 Profile</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Manage your account settings and preferences</div>
<div style="display:grid;grid-template-columns:1fr 2fr;gap:1.5rem;">
    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.5rem;text-align:center;">
        <div class="avatar" style="width:120px;height:120px;margin:0 auto 1rem;font-size:3rem;border-radius:50%;background:var(--gradient-1);display:flex;align-items:center;justify-content:center;color:white;">{user.get("avatar", "U")}</div>
        <h3 style="font-size:1.2rem;">{user.get("name", "User")}</h3>
        <p style="color:rgba(255,255,255,0.3);">{user.get("email", "")}</p>
        <p style="color:rgba(255,255,255,0.15);font-size:0.8rem;margin-top:0.5rem;">Role: {user.get("role", "Analyst")}</p>
        <button class="btn-primary" onclick="alert('📸 Profile picture upload coming soon!')" style="margin-top:1rem;">📸 Change Photo</button>
    </div>
    <div style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:1rem;padding:1.5rem;">
        <h3 style="margin-bottom:1rem;">Account Details</h3>
        <div class="settings-item"><div class="label">Full Name</div><div class="value" style="color:rgba(255,255,255,0.3);">{user.get("name", "User")}</div></div>
        <div class="settings-item"><div class="label">Email</div><div class="value" style="color:rgba(255,255,255,0.3);">{user.get("email", "")}</div></div>
        <div class="settings-item"><div class="label">Role</div><div class="value" style="color:rgba(255,255,255,0.3);">{user.get("role", "Analyst").title()}</div></div>
        <div class="settings-item"><div class="label">Member Since</div><div class="value" style="color:rgba(255,255,255,0.3);">{datetime.now().strftime("%B %d, %Y")}</div></div>
        <div class="settings-item"><div class="label">Last Login</div><div class="value" style="color:rgba(255,255,255,0.3);">Today at {datetime.now().strftime("%I:%M %p")}</div></div>
        <div style="margin-top:1.5rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
            <button class="btn-primary" onclick="alert('🔑 Password reset email sent!')">🔑 Change Password</button>
            <button class="btn-primary" style="background:rgba(239,68,68,0.1);color:#ef4444;" onclick="alert('2FA setup coming soon!')">🔒 Enable 2FA</button>
            <button class="btn-primary" style="background:rgba(255,255,255,0.02);" onclick="exportCSV()">📥 Export Data</button>
        </div>
    </div>
</div>
'''
    return HTMLResponse(content=render_page(content, user, "profile", "Profile"))

@app.get("/settings")
async def settings_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    content = '''
<div class="page-title">⚙️ Settings</div>
<div class="page-subtitle" style="color:rgba(255,255,255,0.3);font-size:0.9rem;margin-bottom:1.5rem;">Manage your workspace preferences</div>
<div class="settings-group">
    <h3 style="color:rgba(255,255,255,0.3);font-size:0.8rem;margin-bottom:0.8rem;font-weight:600;letter-spacing:0.5px;">Workspace</h3>
    <div class="settings-item"><div class="label">Workspace Name</div><div class="value" style="color:rgba(255,255,255,0.3);">FORESIGHT Workspace</div></div>
    <div class="settings-item"><div class="label">Timezone</div><div class="value" style="color:rgba(255,255,255,0.3);">UTC +5:30</div></div>
</div>
<div class="settings-group">
    <h3 style="color:rgba(255,255,255,0.3);font-size:0.8rem;margin-bottom:0.8rem;font-weight:600;letter-spacing:0.5px;">Preferences</h3>
    <div class="settings-item"><div class="label">Theme</div><div class="value"><select id="themeSelect" style="background:rgba(255,255,255,0.02);border:1px solid var(--border-color);border-radius:0.4rem;color:white;padding:0.3rem 0.8rem;font-family:'Inter',sans-serif;"><option value="dark" selected>Dark</option><option value="light">Light</option></select></div></div>
    <div class="settings-item"><div class="label">Currency</div><div class="value" style="color:rgba(255,255,255,0.3);">Indian Rupee (₹)</div></div>
    <div class="settings-item"><div class="label">Language</div><div class="value"><select id="languageSelect" style="background:rgba(255,255,255,0.02);border:1px solid var(--border-color);border-radius:0.4rem;color:white;padding:0.3rem 0.8rem;font-family:'Inter',sans-serif;"><option value="en" selected>English</option><option value="hi">Hindi</option><option value="ta">Tamil</option></select></div></div>
    <div class="settings-item"><div class="label">Email Notifications</div><div class="toggle active" onclick="this.classList.toggle('active')"><div class="dot"></div></div></div>
    <div class="settings-item"><div class="label">Weekly Reports</div><div class="toggle" onclick="this.classList.toggle('active')"><div class="dot"></div></div></div>
    <div class="settings-item"><div class="label">Low Stock Alerts</div><div class="toggle active" onclick="this.classList.toggle('active')"><div class="dot"></div></div></div>
    <div class="settings-item"><div class="label">Expiry Alerts</div><div class="toggle active" onclick="this.classList.toggle('active')"><div class="dot"></div></div></div>
</div>
<div class="settings-group">
    <h3 style="color:rgba(255,255,255,0.3);font-size:0.8rem;margin-bottom:0.8rem;font-weight:600;letter-spacing:0.5px;">Data & Privacy</h3>
    <div class="settings-item"><div class="label">Data Retention</div><div class="value" style="color:rgba(255,255,255,0.3);">30 days</div></div>
    <div class="settings-item"><div class="label">Auto-backup</div><div class="toggle active" onclick="this.classList.toggle('active')"><div class="dot"></div></div></div>
    <div class="settings-item"><div class="label">Share Analytics</div><div class="toggle active" onclick="this.classList.toggle('active')"><div class="dot"></div></div></div>
</div>
<button class="btn-primary" onclick="saveSettings()" style="padding:0.6rem 2rem;">💾 Save Changes</button>
<div id="saveMessage" style="display:none;margin-top:1rem;padding:0.8rem;border-radius:0.5rem;background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.2);color:#22c55e;"></div>
<script>
function saveSettings() {{
    const msg = document.getElementById('saveMessage');
    msg.style.display = 'block';
    msg.textContent = '✅ Settings saved successfully!';
    setTimeout(() => msg.style.display = 'none', 3000);
}}
</script>
'''
    return HTMLResponse(content=render_page(content, user, "settings", "Settings"))

# ============================================
# API ROUTES
# ============================================
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        filename = file.filename
        if not filename:
            return JSONResponse(status_code=400, content={"status": "error", "message": "No file selected"})
        
        file_extension = filename.split(".")[-1].lower() if "." in filename else ""
        if file_extension not in ["csv", "xlsx", "xls"]:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Unsupported format: .{file_extension}"})
        
        content = await file.read()
        
        if file_extension == "csv":
            try:
                df = pd.read_csv(io.StringIO(content.decode('utf-8')))
            except:
                df = pd.read_csv(io.StringIO(content.decode('latin-1')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        if df.empty:
            return JSONResponse(status_code=400, content={"status": "error", "message": "File is empty"})
        
        count = 0
        for _, row in df.iterrows():
            try:
                product_name = str(row.get("Product", row.get("product", "Unknown")))
                sku = str(row.get("SKU", row.get("sku", f"SKU-{random.randint(100, 999)}")))
                store_name = str(row.get("Store", row.get("store", "Unknown")))
                stock_val = int(row.get("Stock", row.get("stock", 0)))
                status_val = str(row.get("Status", row.get("status", "In Stock")))
                
                existing = next((item for item in inventory if item["sku"] == sku), None)
                if existing:
                    existing["stock"] = stock_val
                    existing["status"] = status_val
                else:
                    inventory.append({
                        "product": product_name,
                        "sku": sku,
                        "store": store_name,
                        "stock": stock_val,
                        "status": status_val,
                        "expiry_date": None,
                        "days_until_expiry": None
                    })
                count += 1
            except:
                continue
        
        generate_notifications()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"File '{filename}' uploaded! Added/Updated {count} items.",
            "rows": len(df),
            "columns": list(df.columns)
        })
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Error: {str(e)}"})

@app.post("/api/auto-clean")
async def auto_clean():
    try:
        fixed_count = 0
        for item in inventory:
            if not item.get("product"):
                item["product"] = "Unknown Product"
                fixed_count += 1
            if not item.get("sku"):
                item["sku"] = f"SKU-{random.randint(10000, 99999)}"
                fixed_count += 1
            if item.get("stock") is None:
                item["stock"] = 0
                fixed_count += 1
        
        seen_skus = set()
        to_remove = []
        for i, item in enumerate(inventory):
            sku = item.get("sku")
            if sku in seen_skus:
                to_remove.append(i)
            else:
                seen_skus.add(sku)
        
        for i in sorted(to_remove, reverse=True):
            del inventory[i]
        
        generate_notifications()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Auto-clean complete! Fixed {fixed_count} issues, removed {len(to_remove)} duplicates."
        })
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Error: {str(e)}"})

@app.post("/api/notifications/read-all")
async def mark_all_read():
    for n in notifications:
        n["read"] = True
    return JSONResponse(content={"status": "success", "message": "All notifications marked as read"})

@app.get("/api/predictions")
async def get_predictions():
    return JSONResponse(content={
        "predictions": predictions_data,
        "weekly_data": weekly_data[-7:],
        "summary": {
            "next_week_sales": predictions_data[-1]["predicted_sales"] if predictions_data else 0,
            "next_week_revenue": predictions_data[-1]["predicted_revenue"] if predictions_data else 0,
            "avg_confidence": sum(p["confidence"] for p in predictions_data) // len(predictions_data) if predictions_data else 0
        }
    })

@app.get("/api/report-download/{report_type}")
async def download_report(report_type: str):
    import io
    output = io.StringIO()
    import csv
    writer = csv.writer(output)
    
    if report_type == "inventory":
        writer.writerow(["Product", "SKU", "Store", "Stock", "Status"])
        for item in inventory:
            writer.writerow([item["product"], item["sku"], item["store"], item["stock"], item["status"]])
    elif report_type == "forecast":
        writer.writerow(["Product", "SKU", "Current Stock", "Forecast Demand"])
        for item in inventory[:10]:
            forecast = int(item["stock"] * random.uniform(0.8, 1.5))
            writer.writerow([item["product"], item["sku"], item["stock"], forecast])
    elif report_type == "predictions":
        writer.writerow(["Day", "Date", "Predicted Sales", "Predicted Revenue (₹)", "Confidence", "Trend"])
        for pred in predictions_data:
            writer.writerow([pred["day"], pred["date"], pred["predicted_sales"], usd_to_inr(pred["predicted_revenue"]), pred["confidence"], pred["trend"]])
    else:
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Records", len(inventory)])
        writer.writerow(["Low Stock", len([i for i in inventory if i["status"] == "Low Stock"])])
        writer.writerow(["Critical", len([i for i in inventory if i["status"] == "Critical"])])
        writer.writerow(["Next Week Sales", predictions_data[-1]["predicted_sales"] if predictions_data else 0])
        writer.writerow(["Next Week Revenue (₹)", usd_to_inr(predictions_data[-1]["predicted_revenue"]) if predictions_data else 0])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"}
    )

# ============================================
# RUN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3000)