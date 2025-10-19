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

The jury can change a team's password via `/jury/password`, set the maximum number of originals each team may upload at `/jury/settings`, and delete recordings through `/jury/delete`.

Visit `/` to see links to the login and registration pages. Logged-in users are
automatically redirected to their dashboard or the jury panel.

Teams can view other groups' recordings from the dashboard and submit their own
attempts directly in the browser using the built‑in recorder.

## Scoring

Points on the leaderboard are based on jury judgments:

* **3 points** to the posting team if no other team matches their original.
* **1 point** to each team with a successful attempt when every attempt is a match.
* **2 points** to each successful team and **0** to the poster if at least one but not all teams match.
