# Vite to Next.js Integration

This document describes how the Vite React components have been integrated into the Next.js application.

## Components Integrated

### 1. DataSourceSelector → `/data-source` page
- **Original**: `components/DataSourceSelector.tsx`
- **New Location**: `app/data-source/page.tsx`
- **Functionality**: Allows users to choose between uploading their own CSV or using existing sample data
- **Navigation**: Routes to `/upload` or `/dashboard?source=existing`

### 2. FileUpload → `/upload` page
- **Original**: `components/FileUpload.tsx`
- **New Location**: `app/upload/page.tsx`
- **Functionality**: Handles CSV file upload with drag-and-drop interface
- **Navigation**: Routes to `/dashboard?source=upload` after successful upload

### 3. MainDashboard → `/dashboard` page
- **Original**: `components/MainDashboard.tsx`
- **New Location**: `app/dashboard/page.tsx`
- **Functionality**: Main SQL analytics dashboard with query execution and results
- **Navigation**: Back button routes to previous page based on data source

## Key Changes Made

### 1. Next.js App Router Structure
- Converted from Vite's single-page app to Next.js 13+ App Router
- Each component is now a separate page with its own route
- Used `'use client'` directive for client-side components

### 2. Navigation Updates
- Replaced Vite's state-based routing with Next.js `useRouter` and `useSearchParams`
- Added proper URL parameters to pass data between pages
- Implemented back navigation buttons for better UX

### 3. Dependencies
- Added `lucide-react` for icons (needs to be installed: `npm install lucide-react`)
- All existing dependencies from the original Vite app are compatible

### 4. Main Page Redirect
- Updated `app/page.tsx` to redirect to `/data-source` as the entry point
- This maintains the original app flow while using Next.js routing

## File Structure

```
app/
├── page.tsx                 # Redirects to /data-source
├── data-source/
│   └── page.tsx            # DataSourceSelector component
├── upload/
│   └── page.tsx            # FileUpload component
└── dashboard/
    └── page.tsx            # MainDashboard component
```

## Usage

1. Start the development server: `npm run dev`
2. Navigate to `http://localhost:3000`
3. The app will automatically redirect to the data source selection page
4. Follow the flow: Data Source → Upload (if needed) → Dashboard

## Notes

- All original functionality has been preserved
- The UI and styling remain exactly the same
- State management has been adapted to work with Next.js routing
- The app maintains the same user experience as the original Vite version

