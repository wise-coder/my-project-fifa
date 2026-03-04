# FIFA Stats Platform - Frontend Specification

## Project Overview

- **Project Name**: FIFA Stats Platform
- **Type**: Single Page Web Application (Multi-page frontend)
- **Core Functionality**: A FIFA match stats tracking platform where users can upload match screenshots, view leaderboards, track progress, and receive notifications
- **Target Users**: FIFA gamers who want to track and compare their match statistics

## UI/UX Specification

### Color Palette

- **Primary Background**: #121212 (Very dark gray)
- **Secondary Background**: #1E1E1E (Dark gray for cards)
- **Tertiary Background**: #2D2D2D (Slightly lighter for hover states)
- **Primary Text**: #FFFFFF (White)
- **Secondary Text**: #B0B0B0 (Light gray)
- **Accent Color**: #00FF88 (Neon green for highlights/buttons)
- **Accent Hover**: #00CC6A (Darker neon green)
- **Danger Color**: #FF4757 (Red for errors/delete)
- **Warning Color**: #FFA502 (Orange for warnings)
- **Success Color**: #2ED573 (Green for success)
- **Border Color**: #3D3D3D (Subtle borders)

### Typography

- **Primary Font**: 'Rajdhani', sans-serif (Futuristic/sports feel)
- **Secondary Font**: 'Roboto', sans-serif (Body text)
- **Heading Sizes**:
  - H1: 2.5rem
  - H2: 2rem
  - H3: 1.5rem
  - H4: 1.25rem
- **Body Size**: 1rem (16px)
- **Small Text**: 0.875rem (14px)

### Spacing System

- **Base Unit**: 8px
- **Margins**: 8px, 16px, 24px, 32px, 48px
- **Padding**: 8px, 16px, 24px, 32px
- **Card Padding**: 24px
- **Section Gap**: 32px

### Layout Structure

#### Landing Page (landing.html)

- Full viewport height hero section
- Centered content with logo, title, description
- Two action buttons (Register, Login) centered below
- Dark gradient background with subtle pattern

#### Registration Page (register.html)

- Centered card (max-width: 450px)
- Form with 4 fields in single column
- Dark input fields with light borders
- Submit button full width
- Link to login page below form

#### Login Page (login.html)

- Centered card (max-width: 400px)
- Form with 2 fields in single column
- Dark input fields
- Submit button full width
- Forgot password link
- Link to registration page

#### Dashboard Page (dashboard.html)

- **Navbar** (fixed top): Logo, Username, Notifications icon with badge, Logout button
- **Sidebar** (left, collapsible on mobile): Navigation buttons for sections
- **Main Content**: Dynamic sections based on sidebar selection

### Components

#### Buttons

- Primary: #00FF88 background, #121212 text, rounded corners (8px)
- Secondary: Transparent with #00FF88 border
- Danger: #FF4757 background
- States: Hover (darken 10%), Active (scale 0.98), Disabled (opacity 0.5)

#### Cards

- Background: #1E1E1E
- Border: 1px solid #3D3D3D
- Border-radius: 12px
- Box-shadow: 0 4px 20px rgba(0,0,0,0.3)

#### Form Inputs

- Background: #2D2D2D
- Border: 1px solid #3D3D3D
- Focus border: #00FF88
- Border-radius: 8px
- Padding: 12px 16px

#### Tables

- Header background: #2D2D2D
- Row hover: #252525
- Border: 1px solid #3D3D3D

#### Progress Bars

- Background track: #2D2D2D
- Fill: #00FF88 (gradient optional)
- Height: 20px
- Border-radius: 10px

#### Notifications Badge

- Background: #FF4757
- Position: top-right of icon
- Size: 18px circle

### Responsive Breakpoints

- Mobile: < 576px
- Tablet: 576px - 992px
- Desktop: > 992px

### Animations

- Page transitions: Fade in (0.3s ease)
- Button hover: Scale 1.02, background transition (0.2s)
- Card hover: Subtle lift (translateY -2px)
- Sidebar toggle: Slide (0.3s ease)

## Functionality Specification

### Landing Page

- Static display page
- Two buttons navigate to register.html and login.html
- No JavaScript required for basic functionality

### Registration Page

- Form validation:
  - Username: Required, min 3 characters
  - Email: Required, valid email format (regex)
  - Password: Required, min 6 characters
  - Confirm Password: Must match password
- Show error messages below invalid fields
- On successful validation: Show success alert and redirect to login (simulated)
- Backend integration point: POST /api/register

### Login Page

- Form validation:
  - Email: Required, valid format
  - Password: Required
- Show error for invalid credentials (simulated)
- On success: Redirect to dashboard.html
- Backend integration point: POST /api/login

### Dashboard Page

#### Navigation Bar

- Logo: Clickable, returns to dashboard home
- Username: Display logged-in user name
- Notification icon: Shows unread count badge
- Logout button: Clears session, redirects to landing

#### Sidebar Navigation

- Upload Screenshot - shows upload section
- Leaderboard - shows leaderboard table
- Progress - shows user progress stats
- Notifications - shows notifications list

#### Main Content Sections

**1. Upload Screenshot Section**

- File input for image upload (accept: .jpg, .jpeg, .png)
- Image preview area (shows uploaded image thumbnail)
- Upload button (submits to backend)
- Backend integration point: POST /api/upload-screenshot

**2. Leaderboard Section**

- Table with columns: Rank, Player Name, Total Score
- Sample data (placeholder)
- Backend integration point: GET /api/leaderboard

**3. Progress Section**

- Stats cards: Matches Played, Wins, Losses, Total Points
- Progress bar: Win Rate percentage
- Backend integration point: GET /api/user/progress

**4. Notifications Section**

- List of notification items
- Each item: Icon, message, timestamp
- Unread indicator (bold text)
- Backend integration point: GET /api/notifications

## File Structure

```
football/
├── SPEC.md
├── landing.html
├── register.html
├── login.html
├── dashboard.html
└── script.js
```

## External Dependencies (CDN)

- Bootstrap 5.3.0 CSS
- Bootstrap 5.3.0 JS (Bundle)
- Google Fonts: Rajdhani, Roboto
- Font Awesome 6.4.0 (Icons)

## Acceptance Criteria

### Landing Page

- [ ] Dark background (#121212) is visible
- [ ] App name "FIFA Stats" displayed prominently
- [ ] Description text is readable
- [ ] Register and Login buttons are visible and styled

### Registration Page

- [ ] Form is centered on page
- [ ] All 4 fields are present
- [ ] Validation shows error for mismatched passwords
- [ ] Validation shows error for invalid email format
- [ ] Submit button is functional

### Login Page

- [ ] Form is centered on page
- [ ] Email and Password fields present
- [ ] Forgot password link is visible
- [ ] Submit button is functional

### Dashboard Page

- [ ] Navbar is fixed at top
- [ ] Sidebar is visible on desktop, collapsible on mobile
- [ ] All 4 sections are accessible via sidebar
- [ ] Image upload shows preview
- [ ] Leaderboard table displays sample data
- [ ] Progress bars are visible
- [ ] Notifications show sample data

### General

- [ ] Dark theme consistent across all pages
- [ ] Responsive on mobile and desktop
- [ ] Bootstrap 5 components used
- [ ] JavaScript handles section switching
- [ ] Comments indicate backend integration points
