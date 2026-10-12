# Thingbd

Company website for **thingbd.com**: Django + SQLite, with a custom-built dashboard for managing all site content.

## Project structure

```
thingsbd/
├── manage.py
├── requirements.txt
├── .env.example            # copy to .env for production
├── config/                 # BACKEND – project settings & root URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── apps/                   # BACKEND – business logic (models, views, forms)
│   ├── core/               # shared base models, SiteSettings, context processor
│   ├── website/            # public pages: home, services, portfolio, about, pages
│   ├── blog/               # blog posts & categories
│   ├── leads/              # contact form & lead inbox
│   └── dashboard/          # custom admin dashboard (login, settings, CRUD screens)
├── templates/              # FRONTEND – HTML
│   ├── website/            # public site (base, pages/, partials/, blog/)
│   ├── dashboard/          # custom dashboard (base, auth/, settings/, account/, partials/, widgets/)
│   └── 404.html, 500.html
├── static/                 # FRONTEND – CSS, JS, images
│   ├── website/            # css/style.css, js/main.js
│   ├── dashboard/          # css/dashboard.css, js/dashboard.js
│   └── img/
├── media/                  # uploaded files (logos, images) – not in git
└── db.sqlite3              # database – not in git
```

**Frontend** = `templates/` + `static/` (HTML, CSS, JS rendered by Django).
**Backend** = `config/` + `apps/` + the SQLite database.

## Run locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_content       # starter content (safe to re-run)
python manage.py createsuperuser
python manage.py runserver
```

- Website: http://127.0.0.1:8000/
- Dashboard: http://127.0.0.1:8000/dashboard/ (staff users only)
- Django admin fallback: http://127.0.0.1:8000/django-admin/ (superusers)

## Build phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Project structure, custom dashboard shell: login/logout, sidebar, dashboard home, site settings, profile, password, light/dark mode, mobile layout | ✅ Done |
| 2 | Dashboard screens for website content: home page, hero stats, marquee, process steps, services, portfolio (with gallery), testimonials, FAQs, team, pages — search, filter, drag ordering, visibility toggle, bulk actions, image upload, rich-text editor | ✅ Done |
| 3 | Blog management: posts (draft / scheduled / published), categories, status & category filters, bulk publish, staff draft preview, image uploads inside the rich-text editor, SEO character counters, reading time | ✅ Done |
| 4 | Leads inbox: status pipeline with activity log, notes, filters, bulk status, CSV export (filtered or selected), new-lead email alerts (several recipients) + optional auto-reply, sidebar badge, pipeline summary | ✅ Done |
| 4+ | SEO on every page: meta title, description, multiple keywords (chips), share image; site-wide defaults; Open Graph + Twitter tags; live Google preview in editors | ✅ Done |
| 5 | Production deploy: `.env`, Gunicorn/Nginx or cPanel, backups | Next |

## Tests

```powershell
python manage.py test
```
