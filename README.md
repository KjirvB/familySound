# familySound

A simple FastAPI app for team-based audio challenges.

The HTML templates use the Tailwind CSS CDN for basic styling. Passwords are
hashed using `passlib`'s `pbkdf2_sha256` algorithm so no external dependencies
are required.

## Setup

Install dependencies and run the server:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Audio uploads are stored under `uploads/`.

The jury can change a team's password via `/jury/password`.

Visit `/` to see links to the login and registration pages. Logged-in users are
automatically redirected to their dashboard or the jury panel.
