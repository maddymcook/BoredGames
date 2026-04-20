# BoredGames Final Project

This repository now includes a full-stack setup aligned to the "Building Software with AI" final-project requirements:

- `backend/`: Django + Django REST Framework API with JWT auth and SQLite database.
- `frontend/`: Expo React Native app with Redux Toolkit state management and async middleware (thunks) that calls the backend.

## Requirement Mapping

### 1) Front End

- Expo React app lives in `frontend/`.
- Responsive UI is state-driven in `frontend/App.js`.
- Dynamic data is rendered from API-powered Redux state (`fetchListings` thunk).
- User input creates data via auth and listing forms (`registerAndLogin`, `createListing`).

### 2) Middleware / Side Effects

- Redux Toolkit store is in `frontend/src/store/store.js`.
- Async side effects use `createAsyncThunk` in:
  - `frontend/src/store/authSlice.js`
  - `frontend/src/store/listingsSlice.js`
- Network requests are centralized in `frontend/src/api/client.js`.

### 3) Backend User Data + Endpoints

- Resource-oriented API endpoints are registered under `/api/`:
  - `/api/users/`
  - `/api/listings/`
  - `/api/messages/`
  - `/api/auth/token/`, `/api/auth/token/refresh/`
- Endpoints are implemented with DRF `ModelViewSet`s (supports GET/POST/PUT/PATCH/DELETE by default).

### 4) Database

- Uses SQLite in development (`backend/config/settings.py`).
- Models include users, profiles, listings, and messages in `backend/apps/*/models.py`.

### 5) Best Practices

- Sensitive config uses `.env` files:
  - `backend/.env` (ignored by git)
  - `frontend/.env` (recommended for Expo URL config)
- `.env.example` files provided for both backend and frontend.
- RESTful endpoint naming follows nouns/resources.
- DRY design with reusable API client and Redux slices.
- Appropriate status codes and validation are handled through DRF serializers/viewsets.

## Running the Project

### Backend

1. `cd backend`
2. `python -m venv .venv`
3. Activate venv and run `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`
5. `python manage.py migrate`
6. `python manage.py runserver`

### Frontend (Expo)

1. Open a new terminal and `cd frontend`
2. `npm install`
3. Copy `.env.example` to `.env`
4. `npm run start`

Set `EXPO_PUBLIC_API_BASE_URL` to your backend API base URL if different from local defaults.
