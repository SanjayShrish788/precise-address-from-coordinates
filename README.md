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

## Setup

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

## Notes

- `.env` is ignored by git to keep API keys private.
- Use `.env.example` as the template for required environment variables.
