# CHAT PASSPORT: LegisQ

**Current Date:** 2026-01-28
**Project:** LegisQ
**Description:** Legislation dashboard and MP performance tracker.

---

## 🚀 Tech Stack
- **Backend Framework:** Flask (Python)
- **Database:** **Google Firestore (Firebase)**
    - *Note:* SQLite is **NOT** used.
- **Frontend:** HTML, CSS, JavaScript (Vanilla)
    - **CSS Framework:** Custom "Glassmorphism" Design System (Vanilla CSS).
- **Authentication:** Admin Login (Environment Variables: `ADMIN_USERNAME`, `ADMIN_PASSWORD`).

---

## 📂 File Structure & Key Files

### Root Directory
- **`app.py`**: The core application entry point.
- **`serviceAccountKey.json`**: **CRITICAL**. The Firebase Admin SDK credential.
- **`load_data.py`** & **`reset_db.py`**: Utility scripts to populate or clear the Firestore database.
- **`universal_upload.py`**: Main unified script for uploading Excel data to Firebase.

### `templates/` (HTML)
- **`index.html`**: The public home page (Bills).
- **`mps.html`**: Public dashboard (MPs).
- **`current_affairs.html`**: Public news page.
- **`admin.html`**: Admin dashboard.
- **`login.html`**: Login page.

### `static/`
- **`css/style.css`**: The main stylesheet.

---

## 💾 Data Models (Firestore)

### Collection: `bills`
- `title` (string): Title of the bill. **(Document ID)**
- `status` (string): e.g., "Passed", "Pending".
- `category` (string): e.g., "Education", "Finance".
- `date_introduced` (string): YYYY-MM-DD format.
- `summary` (string): Short description.
- `file_path` (string): Filename of PDF in static/dataset folder.

### Collection: `mps`
- `name` (string): MP Name.
- `state` (string): State represented.
- `house` (string): "Lok Sabha" or "Rajya Sabha".
- `constituency` (string): Area represented.
- `session` (string): Session name.
- `questions` (number): Question count.
- `debates` (number): Debate participation count.
- `attendance_pct` (number): Attendance percentage.

### Collection: `current_affairs`
- `headline` (string): Main headline.
- `date` (string): Date of news.
- `summary` (string): Short summary.
- `link` (string): URL to full article.

---

## ⚠️ Important Nuances
1.  **Firebase Security Rules:** The app runs on the **Admin SDK** so it bypasses Firestore Security Rules.
2.  **Date Formatting:** Dates are typically stored as strings.
3.  **UI Logic:** if `summary` is empty, the description box is hidden.
