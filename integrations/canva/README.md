# Canva Integration

Creates multi-page Canva designs from a folder of images.

## What it does

The integration uses browser automation to:
1. Open Canva (you must be logged in)
2. Create a new design with the specified page size
3. Upload each image as a page
4. Apply layout and margins

## Browser setup

Start your browser with remote debugging:
```
--remote-debugging-port=9222
```

Supported browsers: Chrome, Brave, Edge. Log into Canva before running the workflow.

## How users interact

In the Canva Design tab, users set the images folder (same as Image Generation), configure page size and margins if needed, then run the workflow. The app connects to the browser, creates the design, and uploads images. Progress is shown in the UI.

## Output

A Canva design with one page per image. Users can then edit or export from Canva.
