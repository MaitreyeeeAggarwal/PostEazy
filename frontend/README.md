# PostEazy Frontend Web Application

High-performance, modern single-page application (SPA) for **PostEazy Content Engine**.

## Architecture & File Structure

```
c:\development\SiH\Backend\frontend/
├── index.html        # Main landing page, Hero section, Studio Workbench, Auth Modal & Footer
├── css/
│   └── styles.css    # Design system, dark glassmorphism, responsive grid, animations
├── js/
│   └── app.js        # API integration, JWT Auth, tab switching, script editor, slide previewer
└── README.md         # Project documentation
```

## Features

1. **Hero Section & Landing Showcase**:
   - Hero banner with gradient typography.
   - Core value metrics (10x speed, 2 pipelines, 100% source faithfulness).
2. **Authentication Modal**:
   - Register (`POST /api/auth/register`) and Login (`POST /api/auth/login`).
   - Stores JWT token in `localStorage` for authorized endpoints.
3. **Content Generation Studio**:
   - **Pipeline Switcher**: Pipeline B (Faceless Video) vs Pipeline A (Static Posts).
   - **Platform Preset Selector**: Instagram (bold/energetic) vs LinkedIn (insightful/precise).
   - **Document Drag & Drop Upload**: Supports PDF, PPTX, DOCX, TXT, MD up to 25MB.
   - **Controls**: Duration input (`15s`–`90s`) & Aspect ratio dropdown (`Shorts 9:16`, `Feed Carousel 4:5`, `Landscape 16:9`).
   - **Kinetic Render Button**: One-click generation trigger with live progress bar polling.
4. **Visual Deliverables Preview**:
   - Interactive 4:5 / 1:1 Static Carousel slide previewer with next/prev controls.
   - HTML5 video player and download link for faceless video MP4 files.

## Running the Frontend

Simply serve this directory with any web server (or open `index.html` directly in your browser):

```bash
# Option 1: Live Server or python http.server
cd c:\development\SiH\Backend\frontend
python -m http.server 3000

# Option 2: Access served directly by FastAPI at http://localhost:8000
```
