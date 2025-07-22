# Gold Star App

## Prerequisites
- **Python** 3.11 or newer
- **Node.js** and **npm** (tested with Node 20)
- Optional: **Docker** and **Docker Compose** for containerized runs
- Optional: a Kubernetes cluster for deployment

## Installing and Running the Frontend
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The Vite dev server will provide a local URL, typically `http://localhost:5173`.

## Installing and Running the Backend
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install Python requirements:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Start the API server with Uvicorn:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be available on `http://localhost:8000`.

## Using Docker Compose
The repository contains a `docker-compose.yml` file that builds and runs both
services:

```bash
docker-compose up --build
```

The backend will be exposed on port `8000` and the frontend on port `80`.

## Deploying with Kubernetes
A basic `kubernetes.yaml` file is provided for deploying the backend and
frontend. Apply it to your cluster with:

```bash
kubectl apply -f kubernetes.yaml
```

This creates deployments and services for both components. Ensure the container
images referenced in the YAML have been built and pushed to a registry that your
cluster can access.
