# Django Excel-to-Web App Starter Template

A production-ready Django starter template for converting Excel-based workflows into secure, scalable web applications.
This template standardizes authentication, authorization, audit logging, and UI styling so new projects can be spun up quickly and consistently.

---

## 📌 Purpose

This template is designed to be reused as a **base project** for:

- Excel → Web App conversions
- Internal admin tools
- Operational dashboards
- Client-specific data management systems

It enforces:
- Clean architecture
- Role-based access control
- Page-level permissions
- Consistent UI/UX using TailwindCSS

---

## 🚀 Features

- Django project preconfigured with:
  - Custom user model
  - Role-based access (SuperUser / Admin / Standard)
  - Page-level permission system
  - Audit logging
  - Timestamped models
- Environment-based configuration using `.env`
- MySQL & PostgreSQL support
- TailwindCSS (local build - no CDN)
- Permission-aware UI rendering
- Clean structure for client-specific apps

---

## 🧱 Tech Stack

- **Backend:** Django
- **Database:** MySQL / PostgreSQL
- **Frontend:** Django Templates + TailwindCSS
- **Auth:** Custom user roles & permissions
- **Styling:** TailwindCSS (compiled locally)

---

## 📁 Project Initialization

### 1. Clone the Template Repository
```bash
git clone https://github.com/vilash99/excel_invoicing.git
```

### 2. Rename `excel_invoicing` to Your Project Name and do following steps to remove github old logs
- Show hidden file/folder and delete `.git` folder
- Reinitialize the git by `git init`
- Add all untracked changes `git add .`
- Commit changes `git commit -m "First Commit"`


## 🐍 Python Environment Setup

### 3. Create Virtual Environment
```bash
python -m venv .venv
```

### 4. Activate Virtual Environment

**Windows**
```bash
.\.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

---

### 6. Create Database

Create a new database using MySQL or PostgreSQL. Create with name that you will going to use in `.env` file in `DB_NAME`.

### 7. Gather Database Credentials

You will need:

- Database name
- Database user
- Database password
- Host
- Port (If given)

### 8. Configure `.env`

Create a .env file and add:

```yaml
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306 # MySQL default
```

Update port if using PostgreSQL.

---

## 🔄 Migrations & Server Setup

### 9. Create Migrations (not-needed)
```bash
python manage.py makemigrations
```

### 10. Apply Migrations
```bash
python manage.py migrate
```

### 11. Create Superuser
```bash
python manage.py createsuperuser
```

### 12. Run Development Server
```bash
python manage.py runserver
```

### 13. Open Django Admin

http://127.0.0.1:8000/admin/

Log in using the superuser credentials you've just created and follow steps given in Step 15.

---

## 👤 Initial System Configuration

### 14. Configure Superuser Profile

1. Go to Users
2. Select the superuser you've created.
3. Add: `First Name`, `Last Name`
4. (Optional) Disable forced password change by uncheck `Is first login` checkbox.

Save changes.

## 🎨 Branding & UI Customization

Edit:
```text
templates/_base.html
```

Update:
- `PROJECT NAME` in `<title>` tag
- `PROJECT NAME` in navbar
- `project-name` from image `alt` attributes
- `TIME_ZONE = 'UTC'` to client timezone

Add favicon:
```text
static/images/favicon.ico
```
---

## 🧩 Creating a Client App

Each client or module should live in its own Django app.

### 17. Create Models

Create new app inside clientapps folder
1. Create empty __init__.py file in clientapps folder.
2. Run below command to create app. Make sure to create empty folder with same name
```
python manage.py startapp profiles clientapps/profiles
```

In `clientapps/models.py`:

- Define models
- All models must inherit:
```python
from common.models import TimeStampedModel
```

Register models in `clientapps/admin.py`.

### 18. Register App

Add to `project/settings.py`:

```python
INSTALLED_APPS += [
    'clientapp.appname',
]
```

### 19. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

Confirm models appear in `/admin` page.

### 20. URLs

Project `urls.py`:

```python
path('appname/', include('clientapp.appname.urls')),
```

Client app `urls.py`:
```python
app_name = 'clientapp'
```
---

## 🎨 TailwindCSS Setup

### 21. Install Node Dependencies
```bash
npm install -D tailwindcss@3.4.18 postcss autoprefixer
```

### 22. Tailwind Configuration
Create `tailwind.config.js` in same level of `manage.py` file and add below code.

```js
module.exports = {
  content: ['./templates/**/*.html'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 23. Create Input CSS

Create file `static/css/input.css`.

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 24. Build Tailwind CSS
Generate `static/css/output.css` css code using below command.
```bash
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
```

### 25. Update Base Template

Add above newly generated `output.css` in `_base.html` into `<head>` tag:
```html
<link rel="stylesheet" href="{% static 'css/output.css' %}">
```

Remove:
```html
<script src="https://cdn.tailwindcss.com"></script>
```

## 🔐 Permissions in Views & Templates

### 26. Views (Not required)

Add the mixin:
```
PagePermissionContextMixin
```
(after `PageAccessRequiredMixin`)

### 27. Templates

At the top:
```django
{% extends "_base.html" %}
{% load access_tags %}
```

### 28. Conditional UI Rendering (whenever needed)
```django
{% if user|has_access:"doctor_sites:view" %}
  <a href="{% url 'providers:doctor_sites' %}">
    Doctor Sites
  </a>
{% endif %}
```

## 📐 Page Naming Convention
If you are adding any page, make sure follow below standard naming.
- Page Name: `App Countries`
- Page Code: `clientapp_countries`

Always prefix page codes with the app name.

---
