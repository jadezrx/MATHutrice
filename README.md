# MATHutrice

LLM-based tutor that helps EPF first-year students practise mathematical tools through notions, competences and training.

Students land on a home page after signing in and pick a module (for example "Trigonométrie"). A module page shows a short description of the notion, a global progression bar, the skills evaluated at EPF (those in Moodle), a quick-access "M'entraîner" button, and progression by subtheme. A chat lets students ask the tutor questions, and answers stream word by word. Teachers and admins have their own pages (see `CONTEXT.md` for the vocabulary).

![Home page mockup](https://github.com/user-attachments/assets/faa9c372-129c-4414-9160-f5f263b10f12)

## Run it locally

Requirements:

- [uv](https://docs.astral.sh/uv/), which installs the Python version in `.python-version` (3.14) and the dependency versions in `uv.lock`.
- An API key for an OpenAI-compatible **LLM endpoint**. The default is Mistral: get a key at <https://console.mistral.ai> (a free account works).

```sh
git clone -b course-2026 <your fork URL> mathutrice
cd mathutrice
uv sync
. .venv/bin/activate        # Windows: .venv\Scripts\activate
cp .env.example .env
```

Edit `.env` and set `LLM_API_KEY`. Leave everything else as it is for a local run.

Start the application from the repository root:

```sh
uvicorn mathutrice.app:app --port 8000
```

Then open <http://localhost:8000/>. With the default `.env` you are redirected to the dev sign-in page (see below).

To check that a clone works, and for troubleshooting (older uv, installing without uv), follow [`docs/smoke-test.md`](docs/smoke-test.md).

### Environment variables

Every variable is listed, with comments, in [`.env.example`](.env.example). The application refuses to start when a required one is missing.

| Variable | Purpose |
| --- | --- |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | The **LLM endpoint**. `LLM_API_KEY` is required. To use another endpoint, change all three together. |
| `DATABASE_URL` | SQLite by default (`sqlite:///./mathutrice.db`); PostgreSQL for deployed environments. |
| `SESSION_SECRET` | Signing key for session cookies. Required. |
| `AUTH_MODE` | `entra` (default when unset) or `dev`. See below. |
| `DEV_LOGIN_KEY` | Optional shared key protecting the dev sign-in. Only used when `AUTH_MODE=dev`. |
| `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `REDIRECT_URL`, `POST_LOGOUT_REDIRECT_URL` | Microsoft Entra ID settings. Required when `AUTH_MODE=entra`, unused otherwise. |

## Signing in

### Production: Microsoft Entra ID

With `AUTH_MODE` unset or set to `entra`, users sign in through Microsoft Entra ID. This needs `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `REDIRECT_URL` and `POST_LOGOUT_REDIRECT_URL`. Only `@epfedu.fr` and `@epf.fr` addresses are accepted.

### Development: the connexion de développement

`.env.example` sets `AUTH_MODE=dev`, so a fresh clone runs without Entra credentials. The **connexion de développement** signs you in as any user with no proof of identity: you choose an `@epfedu.fr` or `@epf.fr` email address and a role (Student, Teacher or Admin). A red banner shows on every page, and the application prints a `WARNING: AUTH_MODE=dev` line at startup. The routes `GET /dev/login` and `POST /dev/login` only exist in this mode.

Optionally set `DEV_LOGIN_KEY` to require a shared key on the sign-in form. An empty value means no key. The key is ignored, with a startup warning, when `AUTH_MODE=entra`.

> **Set a real `SESSION_SECRET` on anything reachable by others.** The value in `.env.example` is a public placeholder. While it is unchanged, anyone can forge a session cookie and skip `DEV_LOGIN_KEY` entirely.

`REDIRECT_URL` and `POST_LOGOUT_REDIRECT_URL` are Entra settings: in dev mode they are unused, and logging out clears the session and returns to `/`, which redirects to the dev sign-in page.

#### Scripted sign-in

`POST /dev/login` takes form fields `email` (required), `name`, `role` and `key`. Keep the session cookie between requests with a cookie jar:

```sh
# sign in as a teacher (add -d key=... if DEV_LOGIN_KEY is set)
curl -s -c cookies.txt -o /dev/null -w '%{http_code}\n' \
  -d email=prof@epfedu.fr -d role=Teacher \
  http://localhost:8000/dev/login

# reuse the session
curl -s -b cookies.txt http://localhost:8000/
```

The sign-in answers `303` with the cookie set. It answers `401` for a wrong key, `403` for an address outside `@epfedu.fr` / `@epf.fr`, and `400` for an unknown role.

## Deployment checklist

- [ ] `AUTH_MODE` non défini ou `entra`. Never `dev`.
- [ ] `SESSION_SECRET` set to a long random value, not the placeholder.
- [ ] `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `REDIRECT_URL` and `POST_LOGOUT_REDIRECT_URL` set for Entra.
- [ ] `DATABASE_URL` pointing at PostgreSQL.
- [ ] `LLM_API_KEY` set for the **LLM endpoint**. On Mistral's free plan, requests may be used for training: turn that off under Privacy in the admin panel before using real data.

## Contributing

Package boundaries are machine-checked: read [`mathutrice/README.md`](mathutrice/README.md) before adding a package or importing across one, then run:

```sh
uv run tach check
uv run python scripts/check_cycles.py
```
