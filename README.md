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

## Deploy to a server (Ubuntu)

On a fresh Ubuntu 22.04/24.04 server, as root:

```bash
curl -fsSL https://raw.githubusercontent.com/Rabbi-2529/thingbd/main/deploy/setup_server.sh -o setup_server.sh
sudo bash setup_server.sh            # or: sudo bash setup_server.sh 147.93.152.43
thingbd-manage createsuperuser       # your dashboard login
```

It installs Python, Nginx and Gunicorn, puts the app in `/srv/thingbd` (code in `app/`,
database in `data/`, uploads in `media/`, settings in `.env`), opens the firewall for web
traffic and sets up daily backups in `/srv/thingbd/backups` (14 days kept).
Previous websites on the server are archived to `/root/pre-thingbd-backup-<date>/` and disabled, not deleted.

Point a domain at the server (DNS A records for `example.com` and `www.example.com`), then switch to HTTPS:

```bash
curl -fsSL https://raw.githubusercontent.com/Rabbi-2529/thingbd/main/deploy/enable_domain.sh -o enable_domain.sh
sudo bash enable_domain.sh thingbd.com you@example.com
```

It reuses or requests a Let's Encrypt certificate, redirects www / http / the bare IP to `https://<domain>`,
updates `.env` (allowed hosts, CSRF origins, secure cookies) and verifies automatic certificate renewal.

- Update to the latest GitHub version: `sudo thingbd-update`
- Run any Django command: `thingbd-manage <command>`
- Logs: `journalctl -u thingbd -f`
- Change settings (email, domain): `nano /srv/thingbd/.env`, then `systemctl restart thingbd`

## Tests

```powershell
python manage.py test
```
