Here’s a tailored subtask breakdown for your stack:

Backend: Python + Flask + SQLite
Frontend: Vite + React + TypeScript
Auth style: Modern & secure → short-lived access token (in memory / localStorage) + long-lived refresh token in HttpOnly cookie (prevents XSS stealing refresh token)

Summary / Outline

Backend setup & models (4–5 tasks)
Auth endpoints & token logic (core login/refresh/logout)
Security & middleware
Frontend login + token handling
Protected routes & auto-refresh
Testing & polish

Pick ~10–14 tasks to start with (the starred ones ★ are highest priority for MVP).
Backend-focused subtasks

★ Install dependencies: flask, flask-jwt-extended, flask-sqlalchemy, werkzeug (for password hashing)
★ Set up Flask app + config: SECRET_KEY, JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES (~15–60 min), JWT_REFRESH_TOKEN_EXPIRES (~7–14 days), JWT_TOKEN_LOCATION = ["cookies"]
★ Create SQLite models: User (id, username/email, password_hash)
★ Implement password hashing utils (werkzeug.security.generate_password_hash / check_password_hash)
★ POST /register endpoint: validate input, hash password, save user
★ POST /login endpoint: verify credentials → create_access_token + create_refresh_token → set_refresh_cookies(response), return {"access_token": ...} in body
★ POST /refresh endpoint: @jwt_required(refresh=True) → new access token → set_access_cookies(response) if using cookie mode, or return in body
★ GET/POST /logout endpoint: unset_jwt_cookies(response) + optional refresh token invalidation (blacklist or simple DB flag)
★ Create @jwt_required() protected test route (e.g. /profile) that returns current user identity
Add global JWT error handlers (expired, invalid, missing → 401/422 responses)
(Later) Add refresh token storage/rotation/blacklist in DB for true revocation support

Frontend-focused subtasks (React + TS + Vite)

★ Create Auth context / store (useState / Zustand / Redux) to hold: accessToken (string | null), user (object | null), isAuthenticated (boolean)
★ Build Login page/component: form → onSubmit → axios.post('/login') → save access_token to state → redirect
★ Set up Axios instance + request interceptor: if accessToken → add Authorization: Bearer ${accessToken} header
★ Handle 401 response globally (response interceptor): try /refresh → if success → update accessToken & retry original request; else → logout & redirect to login
★ Create useAuth hook or ProtectedRoute component: if !isAuthenticated → redirect to /login
★ Implement logout: clear state + axios.post('/logout') → redirect to login
Add loading/error states + form validation (zod / react-hook-form) on login
(Nice to have) Add "Remember me" → longer refresh cookie lifetime via backend config

Quick security & dev polish tasks

★ Enforce CORS correctly (flask-cors) – allow credentials, origin from http://localhost:5173 (vite default)
Set cookie flags in Flask: secure=True (only prod), samesite="Strict" or "Lax", httponly=True for refresh
Write basic tests: pytest for login/refresh/protected route
Add rate limiting on /login and /refresh (flask-limiter)
Document flow in README (sequence diagram optional)

Suggested first GitHub milestones

MVP Login — tasks 1–6 + 12–14
Token Refresh & Protected Routes — 7 + 9 + 15–16
Logout + Security Basics — 8 + 17 + 20–21

Start with backend config + models + login endpoint — once /login returns access token + sets refresh cookie, move to frontend.