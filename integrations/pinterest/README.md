# Pinterest Integration

Publishes pins to Pinterest with title, description, and keywords from the design package.

## What it does

The integration uses browser automation to:
1. Connect to an existing browser (you must be logged into Pinterest)
2. Create a pin for each image
3. Fill title, description, and keywords from the design package
4. Upload images and publish

## Browser setup

Start your browser with remote debugging:
```
--remote-debugging-port=9222
```

Use the "Launch Browser" button in the System & Prerequisites section, or start manually. Log into Pinterest before continuing.

## How users interact

In the Pinterest Publishing tab, users ensure the design package and images are ready, then run the workflow. The app prepares a folder with the config and images, then publishes each pin via the browser. Progress is shown in the UI.

## Multiprocessing

Because Streamlit's event loop is incompatible with Playwright's subprocess handling, the publisher runs in a separate process. This is transparent to users.

## Output

Published pins on Pinterest. A local folder is created with the config and a record of published pins.
