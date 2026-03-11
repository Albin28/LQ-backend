# LegisQ (LQ) - Advanced Legislative Transparency & Analysis Platform

![LegisQ Banner](https://raw.githubusercontent.com/Albin28/legisq-bills/main/static/banner.png) <!-- Note: Replace with actual banner if available or generic placeholder -->

## 📜 1. Abstract & Concept
**LegisQ** is a state-of-the-art digital ecosystem designed to bridge the gap between complex legislative processes and citizen awareness. In a modern democracy, accessibility to parliamentary data is often hindered by fragmented sources and antiquated interfaces. 

LegisQ solves this by providing a unified, high-performance platform that tracks **Bills**, monitors **MP (Member of Parliament) Performance**, and aggregates **Real-time News**. By leveraging modern web technologies and cloud-native architectures, LegisQ transforms raw government data into actionable insights through interactive visualizations and a premium, user-centric interface.

---

## 🚀 2. Core Features

### 🏛️ Public User Portal
*   **Dynamic Bills Dashboard**: A comprehensive list of all legislative bills with real-time search and filtering by status (Introduced, Passed, Assented, Lapsed).
*   **Analytical Visualizations**: Integrated **Chart.js** doughnut charts providing a bird's-eye view of legislative progress across both houses of parliament.
*   **Legislative Document Access**: Direct integration for downloading official PDF and DOCX bill copies, ensuring transparency.
*   **MP Performance Index**: A dedicated section to monitor MPs, filterable by State, House (Lok Sabha/Rajya Sabha), and constituency. It tracks attendance, questions raised, and debates participated in.
*   **Current Affairs Hub**: A real-time news aggregator that pulls the latest national updates from premium RSS feeds like NDTV, The Hindu, and Indian Express.

### 🔐 Administrative Command Center
*   **Secure Authentication**: Protected via **Firebase Authentication**, ensuring only authorized personnel can modify critical legislative data.
*   **Granular Data Control (CRUD)**: Full creation, reading, updating, and deletion capabilities for both Bills and MP records.
*   **Automated Document Storage**: A specialized workflow that uploads bill documents directly to a public GitHub repository via API, generating permanent raw URLs for public access.
*   **Bulk Data Integration**: Support for bulk uploading records via Python scripts, ideal for initial migration or periodic data syncs.
*   **Database Reset Utility**: One-click functionality for clearing Firestore collections during development or rebranding phases.

---

## 🎨 3. UI/UX Design Philosophy
LegisQ adopts a **"Glassmorphic Dark-Mode"** aesthetic, aimed at providing a premium, non-distracting environment for data analysis.

*   **Design Tokens**: Utilizing a curated palette of deep blues (`#0d47a1`), sleek slate backgrounds (`#0f172a`), and vibrant accent gradients.
*   **Micro-animations**: Subtle hover transitions and fade-in animations using CSS3 for a "living" interface.
*   **Responsive Layouts**: A fully responsive CSS Grid and Flexbox architecture that ensures the dashboard is as functional on a smartphone as it is on a 4K monitor.
*   **Component-based Architecture**: Reusable Jinja2 templates and modular CSS components for consistency across the public and admin portals.

---

## 🏗️ 4. System Architecture

The project is built on a **Decoupled Serverless Architecture**, ensuring maximum scalability and minimal maintenance overhead.

### 🖼️ Frontend Layer
*   **Languages**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript (ES6+).
*   **Libraries**: 
    *   `Chart.js`: For data visualization.
    *   `Jinja2`: Python-based templating for dynamic server-side rendering.

### ⚙️ Backend Layer
*   **Framework**: `Flask` (Python 3.10+).
*   **Logic**: Serverless functions hosted on Vercel, handling API routes for both data retrieval and administrative management.
*   **Middleware**: `flask-cors`, `feedparser`, `python-dotenv`.

### ☁️ Cloud & Infrastructure
*   **Database**: `Google Cloud Firestore` (NoSQL). Chosen for its real-time sync capabilities and flexible schema.
*   **Authentication**: `Firebase Auth`. Handles secure tokens and admin session management.
*   **File Storage**: `GitHub API content management`. Utilizing an Albin28/legisq-bills repository as a robust, version-controlled storage backend for legislative documents.
*   **Deployment**: `Vercel`. Automated CI/CD pipeline that triggers builds on every push to the main branch.

---

## 🔄 5. Technical Workflow

### Data Flow Diagram (Conceptual)
1.  **Admin Input**: Admin adds a Bill via the Admin Panel.
2.  **Storage Branching**: 
    *   **Metadata**: Title and status are stored in **Firestore**.
    *   **Document**: The PDF is sent via the **GitHub API** to the storage repo; GitHub returns a raw URL.
3.  **Firestore Commit**: The final Bill record (including the GitHub URL) is committed to the `bills` collection.
4.  **Public Render**: A user visits the public site -> Flask fetches the Firestore collection -> Jinja2 renders cards with direct links to the GitHub-hosted PDFs.

---

## 🛠️ 6. Technology Stack Details

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Server** | Python / Flask | Core application logic and routing. |
| **Database** | Firebase Firestore | Global, real-time NoSQL data storage. |
| **Auth** | Firebase Auth | Secure administrative login. |
| **Hosting** | Vercel | High-availability serverless deployment. |
| **Visuals** | Chart.js | Interactive data analytics. |
| **Storage** | GitHub API | Public-facing document repository. |
| **Styling** | Vanilla CSS | Custom "LegisQ Premium" design system. |

---

## 📂 7. Project Structure
```text
legisq/
├── legisq-public/           # Public-facing dashboard
│   ├── api/index.py        # Flask serverless handler
│   ├── templates/          # Jinja2 HTML templates
│   ├── static/             # CSS, JS, and Images
│   └── vercel.json         # Deployment config
├── legisq-admin/            # Administrative panel
│   ├── api/index.py        # Admin logic & GitHub integration
│   ├── templates/          # Admin UI
│   ├── bulk_upload.py      # Local data utility
│   └── .env                # Secret management
└── ServiceAccountKey.json   # Firebase credentials
```

---

## 📝 8. Developer & Setup Guide

### Local Environment Setup
1.  **Clone the Repository**: `git clone https://github.com/Albin28/legisq-backend.git`
2.  **Install Dependencies**: `pip install -r requirements.txt`
3.  **Environment Variables**: Create a `.env` file with:
    *   `FIREBASE_API_KEY`
    *   `GITHUB_TOKEN`
    *   `FLASK_SECRET_KEY`
4.  **Run Development Server**: `python api/index.py`

### Deployment
The project is configured for **Vercel**. Simply connect your repository to Vercel, and it will automatically handle the build process using the `vercel.json` and `requirements.txt` configurations.

---

## 📈 9. Future Roadmap
*   **AI Integration**: Automated summarization of 50+ page bill documents using LLMs.
*   **User Alerts**: Email/Push notifications for users following specific bills.
*   **Mobile App**: Native Android/iOS applications using React Native or Flutter.

---

## 🤝 10. Conclusion
LegisQ represents a paradigm shift in how citizens consume legislative data. By combining high-end design with robust cloud architecture, it provides a stable, transparent, and beautiful platform that serves both the general public and administrative stakeholders.

---
**Developed by Albin Joseph**  
*Project LegisQ - Empowering Democracy Through Data.*
