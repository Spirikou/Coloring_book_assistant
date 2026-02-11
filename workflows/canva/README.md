# Canva Design Workflow

High-level workflow for creating Canva designs from coloring book images.

## Purpose

Takes the images from the Image Generation step and the design package (title, description) and creates a multi-page Canva layout.

## Inputs

- **Images folder** – Path to folder containing generated images (from state)
- **Design state** – Title and description (used for Canva design metadata)
- **Selected images** – Optional; if set, only these images are used

## Outputs

- A Canva design with one page per image
- Layout and margins applied according to configuration

## Flow

1. User configures page size and margins in the Canva tab
2. User runs the workflow
3. App connects to browser, creates design, uploads images
4. User can edit or export from Canva
