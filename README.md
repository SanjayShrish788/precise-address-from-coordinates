# Coordinates to Address (Flask + Google Geocoding)

Flask web app to convert Google Maps links or raw coordinates into clean postal addresses.

## Features

- Accepts:
  - Raw coordinates (`lat,lng`)
  - Full Google Maps links
  - Short maps links (`goo.gl/maps`, `maps.app.goo.gl`)
- Extracts coordinates robustly from multiple URL formats
- Reverse geocodes with Google Geocoding API
- Smart result selection logic for better address accuracy
- Clean multiline address formatting
- Basic frontend with copy-to-clipboard and map preview

## Project Structure

- `app.py` - Flask app and API routes
- `parser.py` - link parsing and coordinate extraction
- `formatter.py` - address component extraction and formatting
- `templates/index.html` - frontend markup
- `static/script.js` - frontend logic
- `static/style.css` - styling

## Quick Start (For Everyone)

### 1. Download the project

Option A: Git clone

```bash
git clone https://github.com/SanjayShrish788/precise-address-from-coordinates.git
cd precise-address-from-coordinates
```

Option B: ZIP download

1. Open the repository page.
2. Click `Code` -> `Download ZIP`.
3. Extract the ZIP.
4. Open terminal inside the extracted folder.

### 2. Install Python

Install Python 3.10+ from https://www.python.org/downloads/

Verify installation:

```bash
python --version
```

If `python` does not work on macOS/Linux, try:

```bash
python3 --version
```

### 3. Create and activate virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure API key

Create `.env` in the project root (or copy from `.env.example`) and set:

```env
GOOGLE_API_KEY=your_google_api_key_here
REQUEST_TIMEOUT=10
FLASK_DEBUG=1
GEOCODE_SELECTION_DEBUG=0
```

How to get a Google API key:

1. Go to Google Cloud Console.
2. Create/select a project.
3. Enable Geocoding API.
4. Create API key.
5. (Recommended) Restrict the key to Geocoding API.

### 6. Run the app

```bash
python app.py
```

Open in browser:

http://127.0.0.1:5000

### 7. Use the converter

Paste any of the following:

- Raw coordinates: `13.050689,77.577694`
- Full Google Maps URL
- Short URL (`goo.gl/maps`, `maps.app.goo.gl`)

Click `Convert` to get formatted postal address.

## Detailed Setup

1. Create/activate virtual environment (optional if already using one).
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env`:

   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   REQUEST_TIMEOUT=10
   FLASK_DEBUG=1
   GEOCODE_SELECTION_DEBUG=0
   ```

4. Run app:

   ```bash
   python app.py
   ```

5. Open:

   http://127.0.0.1:5000

## API Endpoint

### POST `/convert`

Request:

```json
{
   "link": "13.050689,77.577694"
}
```

Success response:

```json
{
   "status": "success",
   "address": "143 Example Road\nMaruti Nagar, Bengaluru\nKarnataka - 560094\nIndia"
}
```

Error response:

```json
{
   "status": "error",
   "message": "..."
}
```

## Troubleshooting

### Error: missing Google API key

- Ensure `.env` exists in project root.
- Ensure `GOOGLE_API_KEY` is present and non-empty.
- Restart app after editing `.env`.

### Error: API request denied or quota issues

- Check Google Cloud billing and API enablement.
- Verify Geocoding API is enabled.
- Verify API key restrictions.

### Port 5000 already in use

Run on another port:

```bash
python -c "from app import app; app.run(host='127.0.0.1', port=5001, debug=False)"
```

Then open http://127.0.0.1:5001

### Virtual environment activation blocked on PowerShell

Run PowerShell as current user and allow scripts for current session/user as needed, then retry activation.

## Security Notes

- `.env` is ignored by git to keep API keys private.
- Never commit real API keys.
- Use `.env.example` as the template for required environment variables.

## Notes

- This project uses Google Geocoding API for reverse geocoding.
- Parser supports shortened and full maps links plus raw coordinates.
