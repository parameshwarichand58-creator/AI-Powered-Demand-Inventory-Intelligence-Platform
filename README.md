\# FORESIGHT



\## AI-Powered Demand \& Inventory Intelligence Platform



FORESIGHT is an AI-powered inventory intelligence platform designed to help businesses monitor stock levels, track sales, forecast future demand, and make better inventory decisions.



The platform combines inventory management, sales analytics, demand forecasting, expiry monitoring, and automated recommendations in a single dashboard.



\---



\## Features



\### 🔐 Authentication

\- User registration

\- User login

\- Persistent login using browser storage

\- Logout functionality



\### 📦 Inventory Management

\- Add new products

\- Track SKU and supplier information

\- Track purchase and selling prices

\- Monitor stock quantity

\- Set reorder levels

\- Track product expiry dates

\- Delete inventory items

\- Refresh inventory data



\### ⚠️ Inventory Intelligence

\- Low-stock detection

\- Expired-product detection

\- Products expiring within 30 days

\- Inventory status indicators

\- Automated inventory recommendations



\### 💰 Sales Management

\- Record sales

\- Automatically update inventory stock

\- Maintain sales history

\- Calculate total sales quantity

\- Calculate total revenue

\- Track sales records



\### 📊 Analytics

\- Inventory stock analysis

\- Current stock vs reorder level visualization

\- Historical sales statistics

\- Average daily demand

\- Revenue analysis



\### ✦ Demand Forecasting

\- Generate 7-day demand forecasts

\- Analyze historical sales

\- Display predicted demand

\- Visualize forecast trends

\- Generate demand-planning recommendations



\---



\## Technology Stack



\### Frontend

\- React

\- Vite

\- JavaScript

\- Recharts



\### Backend

\- Python

\- FastAPI

\- SQLAlchemy

\- Uvicorn



\### Database

\- SQLite



\### Machine Learning / Data Science

\- Python

\- Pandas

\- NumPy

\- Scikit-learn



# FORESIGHT

## AI-Powered Demand & Inventory Intelligence Platform

FORESIGHT is an AI-powered inventory intelligence platform designed to help businesses monitor stock levels, track sales, forecast future demand, and make better inventory decisions.

The platform combines inventory management, sales analytics, demand forecasting, expiry monitoring, alerts, and automated recommendations in a single dashboard.

---

## 🚀 Features

### 🔐 Authentication

* User registration
* User login
* Persistent login using browser storage
* Logout functionality
* Protected dashboard access

### 📦 Inventory Management

* Add new products
* Track SKU and supplier information
* Track purchase and selling prices
* Monitor stock quantity
* Set reorder levels
* Track product expiry dates
* Delete inventory items
* Refresh inventory data

### ⚠️ Inventory Intelligence

* Low-stock detection
* Expired-product detection
* Products expiring within 30 days
* Inventory status indicators
* Automated inventory recommendations

### 💰 Sales Management

* Record sales
* Automatically update inventory stock
* Maintain sales history
* Calculate total sales quantity
* Calculate total revenue
* Track sales records

### 📊 Analytics

* Inventory stock analysis
* Current stock vs. reorder-level visualization
* Historical sales statistics
* Average daily demand
* Revenue analysis
* Category-wise analysis

### ✦ Demand Forecasting

* Generate 7-day demand forecasts
* Analyze historical sales
* Display predicted demand
* Visualize forecast trends
* Generate demand-planning recommendations

### 📋 Reports & Alerts

* Inventory alerts
* Low-stock alerts
* Expiry alerts
* Demand-based recommendations
* Inventory and sales reports

---

## 🛠️ Technology Stack

### Frontend

* React
* Vite
* JavaScript
* Recharts
* CSS

### Backend

* Python
* FastAPI
* SQLAlchemy
* Uvicorn

### Database

* SQLite

### Machine Learning / Data Science

* Python
* Pandas
* NumPy
* Scikit-learn

---

## 📁 Project Structure

```text
AI-Powered-Demand-Inventory-Intelligence-Platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── raw/
│   └── processed/
│
├── docs/
│   ├── api.md
│   └── architecture.md
│
├── ml/
│   ├── data/
│   ├── evaluation/
│   ├── features/
│   ├── models/
│   ├── prediction/
│   ├── training/
│   └── preprocessing.py
│
├── models/
│   └── README.md
│
├── reports/
│   └── README.md
│
├── .gitignore
└── README.md
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/parameshwarichand58-creator/AI-Powered-Demand-Inventory-Intelligence-Platform.git
```

### 2. Navigate to the project

```bash
cd AI-Powered-Demand-Inventory-Intelligence-Platform
```

---

## 🔧 Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
python -m uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 💻 Frontend Setup

Open a new terminal and navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

## 🔄 Application Workflow

```text
User
  │
  ▼
React Frontend
  │
  ▼
FastAPI Backend
  │
  ├── Authentication
  ├── Inventory Management
  ├── Sales Management
  ├── Analytics
  ├── Forecasting
  ├── Alerts
  └── Recommendations
  │
  ▼
SQLite Database
  │
  ▼
Machine Learning / Forecasting
  │
  ▼
Demand & Inventory Insights
```

---

## 🎯 Project Objective

FORESIGHT aims to help businesses make smarter inventory decisions by combining historical sales data, inventory information, demand forecasting, and automated recommendations.

The platform helps reduce:

* Overstocking
* Stockouts
* Inventory waste
* Expired products
* Poor demand planning

while supporting better:

* Stock planning
* Sales analysis
* Demand prediction
* Inventory monitoring
* Business decision-making

---

## 🔮 Future Enhancements

* Advanced machine learning forecasting models
* Multi-user and role-based access
* Cloud database integration
* Real-time notifications
* Automated purchase-order generation
* Advanced business intelligence dashboards
* Deployment using Docker and cloud platforms
* Integration with external business and retail systems

---

## 👩‍💻 Author

**Parameshwari Chand**

CSE (AI & ML)

---

## 📄 License

This project is intended for educational, portfolio, and demonstration purposes.
