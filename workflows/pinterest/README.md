# Pinterest Publishing Workflow

High-level workflow for publishing coloring book pins to Pinterest.

## Purpose

Takes the design package (title, description, keywords) and images, then publishes one pin per image to Pinterest.

## Inputs

- **Design state** – Title, description, SEO keywords
- **Images folder** – Path to folder containing images
- **Selected images** – Optional; if set, only these images are published

## Outputs

- Published pins on Pinterest
- Local folder with config and published pins record

## Flow

1. User ensures design package and images are ready
2. User runs the workflow (browser must be connected and logged in)
3. App prepares folder with config and copies images
4. App publishes each pin via browser automation
5. Progress is shown in the UI
