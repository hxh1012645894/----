# Frontend development setup

## Install dependencies
```bash
cd frontend
npm install
```

## Development server
```bash
npm run dev
```

The dev server will run on http://localhost:5173 and proxy API requests to the backend (http://127.0.0.1:8000).

## Build for production
```bash
npm run build
```

This will output to the `../static` directory.

## Usage

### Option 1: Using Vite dev server (recommended for development)
```bash
cd frontend
npm run dev
```
Then visit http://localhost:5173

### Option 2: Using backend's built-in server
Visit http://127.0.0.1:8000

The backend server serves the built frontend files from the `static` directory.
