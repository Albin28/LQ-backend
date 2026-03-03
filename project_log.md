# LegisQ Project Log

This document tracks all major changes and decisions made during the project overhaul.

## Phase 1: Firebase Setup

- **Status:** Completed
- **Action:** User created a new Firebase project and provided the `serviceAccountKey.json`. This allows the application to connect to a fresh Firestore database.

## Phase 2: Project Restructuring for Vercel

- **Status:** In Progress
- **Objective:** Re-architect the Flask application to run as a serverless function on Vercel, separating the backend API from the frontend UI.

### Changes:

- **`vercel.json` created:** This file configures Vercel to handle the Python serverless function and defines the routes.
- **`api/index.py` created:** The main `app.py` has been moved and adapted to `api/index.py`, which is Vercel's standard for serverless Python entrypoints.
- **`.gitignore` updated:** Added `serviceAccountKey.json` and other local files to `.gitignore` to prevent committing sensitive credentials and local cache files to the repository.
- **`requirements.txt` updated:** Removed `gunicorn` and `whitenoise` as they are not needed for Vercel. Added `Chart.js` for future data visualization.
- **`app.py` removed:** The original `app.py` is now obsolete and has been removed in favor of `api/index.py`.

## Phase 3: UI Overhaul & Chart Integration

- **Status:** In Progress
- **Objective:** Redesign the frontend to be more modern, visually appealing, and data-driven.

### Changes:

- **`static/css/style.css`:** Completely overhauled the stylesheet.
  - Implemented a new "liquid glass" design system with a dark, futuristic theme.
  - Replaced the static background with a subtle animated gradient for a more dynamic feel.
  - Redesigned all major components: navigation, cards, forms, and buttons for a consistent and modern look.
- **`templates/base.html`:** Updated the base template.
  - Included the Chart.js library.
  - Made the navigation bar smarter: it now correctly highlights the active page and shows an "Admin" button if the user is logged in.
- **`templates/index.html`:** Rebuilt the home page.
  - Added a prominent hero section to create a strong first impression.
  - Implemented a live search and filtering system that works instantly without page reloads.
  - **Integrated a Chart.js doughnut chart** to provide a visual overview of bill statuses.
  - Redesigned the bill cards to be cleaner and more informative.
  - Fixed the PDF download link to work correctly.
- **`api/index.py`:**
  - Modified the `home` route to pass all bill data to the template as a JSON object, enabling the live search and chart functionality.
### Phase 4: MP Dashboard Overhaul

**Date:** 2026-03-03

**Objective:** Redesign the MP dashboard (mps.html) to align with the new UI/UX, implement live client-side filtering, and add a data visualization chart.

**Changes:**

1.  **	emplates/mps.html - Complete Rewrite:**
    *   Replaced the entire file content with a new structure based on the index.html template.
    *   **UI:** Implemented the "liquid glass" design system. Added a new hero section and a more detailed, visually appealing card layout for each MP.
    *   **Controls:** Added a live search input and two dropdowns for filtering by House and State.
    *   **Chart.js Integration:** Added a <canvas> element for a new chart.
    *   **JavaScript:**
        *   Removed the old "show more" and sorting logic.
        *   Added a new <script> that fetches the full MP list as a JSON object from Flask ({{ mps|tojson }}).
        *   Implemented a ilterAndRender() function for instant client-side searching and filtering based on user input.
        *   Added a setupChart() function to create a horizontal bar chart displaying the "Top 10 MPs by Attendance".
    *   **CSS:** Included a <style> block with specific CSS for the new MP card layout.

**Outcome:** The MP dashboard is now fully modernized, offering a vastly improved user experience with interactive filtering and data visualization, consistent with the new design language of the project.
