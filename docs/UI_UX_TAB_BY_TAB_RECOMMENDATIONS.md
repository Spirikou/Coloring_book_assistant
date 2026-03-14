# UI/UX Recommendations — Tab by Tab (Detailed)

One clear, detailed recommendation per tab. No alternatives; implement as described when ready.

---

## Tab 1: Get Started (Guide)

**Goal:** Make the guide scannable, surface the workflow order, and make the Q&A chat easy to find without scrolling.

1. **Add a Quick start block at the top**  
   Right after the main “Get Started” title (and before “What this app does”), add a short block of 3–4 lines: a single-sentence summary of each step in order (e.g. “1. Design Generation — enter your idea, run. 2. Image Generation — set folder, run. 3. Canva Design — check browser, run. 4. Pinterest Publishing — set board, run.”). No expanders. This is the 30-second version. Below it, add a heading like “Detailed steps” and keep the current step expanders.

2. **Make the workflow steps visually ordered**  
   Keep the existing four-column “Recommended workflow” (Design Generation, Image Generation, Canva Design, Pinterest Publishing). Add a thin horizontal progress-style bar under those four columns: four segments in a row (1–2–3–4) so the sequence is clear. Optionally add small step numbers (1, 2, 3, 4) above or inside each column label. No need to reflect actual app state; this is instructional only.

3. **Surface the chat without scrolling**  
   Move “Have questions? Ask about this app” out of the bottom expander. Either:  
   - **Sub-tabs:** Give the Get Started tab two sub-tabs: “Guide” (current content: what this app does, workflow, quick start, detailed steps) and “Ask” (only the chat UI and a short line: “Ask about the app. Answers are based on the documentation.”).  
   Or:  
   - **Prominent strip:** Place a single line near the top of the tab (e.g. right under “What this app does” or under the quick start): “Have questions? [Ask about this app]” as a button or link that scrolls to the chat or opens the chat expander. Put the chat expander directly under that strip so it’s in the first screenful.  
   Pick one of the two (sub-tabs or prominent strip); sub-tabs give a cleaner separation between reading and asking.

4. **Keep “What this app does” in two columns**  
   Leave the two-column bullet layout. Optionally add a subtle border or card style around each column so each block is visually contained. No need to change to four cards unless you want a more compact look.

5. **Step expanders**  
   Keep the step details in expanders. Optionally add one line at the top of each expander: “Estimated time: …” and “Prerequisites: …” so users know what to expect before expanding. All expanders stay collapsed by default except if you want “Detailed steps” itself to be an expander (then only Quick start is always visible).

**Summary for Get Started:** Quick start at top → workflow bar or step numbers → chat in sub-tab or at top → two-column “What this app does” → detailed steps in expanders.

---

## Tab 2: Design Generation

**Goal:** Shorten the main flow, group related controls on one row, and make the “concept” path primary and the “direct” path secondary.

1. **Concept research — one or two rows**  
   Replace the current four full-width blocks (idea, creativity, variations, button) with a compact form.  
   - **Row 1:** Idea text input (about 60–70% width), Creativity selectbox (about 15%), Number of variations selectbox (about 15%). Use columns so the idea field gets most space and the two dropdowns sit on the same row.  
   - **Row 2:** Single button “Generate N Concept Variations” (full width or right-aligned).  
   So: one row of inputs, one row for the action. If the row wraps on narrow screens, keep idea on its own row and put Creativity + Variations + button on the next row.

2. **Selected concepts**  
   Keep the list of selected concepts. Show each as a compact chip or one-line block: “Theme | Style” with a [Remove] button. Put “Add all variations” and the count (e.g. “3 / 5 concepts”) on the same line at the top of the selected list. The “Create custom concept (mix and match)” can stay in an expander as now.

3. **Direct path in an expander**  
   Move “Or describe your coloring book (Direct)” into a collapsible expander. Label it clearly (e.g. “Or describe your coloring book (no concept research)”). Inside: the same text_area for the description, and one row of buttons [Generate] [Clear] under the area. The main tab flow then emphasizes: concept research → select concepts → generate designs. Direct path remains one click away.

4. **Save current design — one row**  
   When a design is loaded and “Saved Designs” is shown, put “Save as” and the primary action on one row: text input “Save as” in about 70% width, [Save Current Design] button in about 30%. No full-width input; the save action is immediately next to the name.

5. **Regenerate (inside “Regenerate” expander)**  
   Keep the custom instructions text_area on its own row (full width). Below it, two rows of buttons:  
   - **Row 1:** [Title] [Interior prompts] [Cover prompts] [Keywords] — single-component regeneration.  
   - **Row 2:** [All] [Full Rerun] — with a short label above or beside (e.g. “Regenerate all” / “Full rerun from concept”) so they’re visually distinct from the single-component buttons.  
   Use shorter labels if needed (e.g. “Interior”, “Cover”) to avoid wrap. All six actions stay; only the grouping and layout change.

6. **Edit and Save expander**  
   Keep Title and Description as they are (each full width). For Keywords: put the keywords text_area and the [Save changes] button on the same row — e.g. keywords in about 80% width, [Save changes] in about 20%, so after editing the user saves without scrolling to the very bottom. The nested expanders (Theme & Artistic Style, Interior prompts, Cover prompts) can stay as they are.

7. **Design Packages selector**  
   No change required. If you show “Save as” only when a design is loaded, you can place “Save as: [input] [Save]” on the same block as the design package selector (one row) to save space.

8. **Content Details tabs (Title & Description, Prompts, Keywords, Download, Theme)**  
   Keep the tabs. In the Prompts tab, use two columns: Interior prompts (left), Cover prompts (right) so both lists are visible with less vertical scroll. Optionally add “Copy all” for the Prompts and Keywords tabs.

9. **Progress overview (five metrics)**  
   Keep the five columns (Theme, Title & Description, Interior, Cover, Keywords). Add a small heading above (e.g. “Design package progress”) so the block is clearly labeled. On narrow widths, consider showing the five metrics in two rows (e.g. 2 + 3) or allow horizontal scroll so they don’t wrap awkwardly.

**Summary for Design Generation:** Concept row (idea + creativity + variations) + button row → selected concepts with “Add all” and count on one line → Direct path in expander → Save as + Save on one row → Regenerate: instructions then two button rows (single-component vs All/Full Rerun) → Edit: Save changes on same row as Keywords → Prompts tab in two columns.

---

## Tab 3: Image Generation

**Goal:** Constrain number and path inputs, put actions next to their controls, and make batch and gallery actions easier to scan.

1. **Output folder**  
   Keep the output folder as a single text input. Add a short caption below it (e.g. “Files will be saved here” or the default path when it’s set) so users see where files go without opening the folder. If feasible, add an [Open folder] button on the same row (e.g. input ~85%, button ~15%) to open the folder in the system file manager.

2. **System & Prerequisites**  
   Keep the expander. Add a one-line status **outside** the expander, on the main tab: e.g. “Browser: ✓ Connected” or “Browser: Not connected” (and optionally “N issues – expand for details”). So at a glance users know if they’re ready without opening the expander. Inside the expander, keep the checks and [Check Browser] [Launch Browser] as they are; optionally use two columns (left: checks list, right: buttons and debug checkbox).

3. **Batch section**  
   When “Run multiple designs (batch)” is expanded, put the batch actions on the first line inside: e.g. “Select designs to run. [Select all] [Clear] [Run] [Quick run]” in one row (or two columns so the buttons don’t wrap). Then show the list of design checkboxes below. So as soon as the user opens the expander they see the actions and the Run/Quick run buttons without scrolling.

4. **Single-design prompts**  
   Keep the prompts text_area full width. Optionally add a row above it: “Prompt set: [Interior ▼] / [Cover ▼]” (or similar) and “Load from design” if applicable, so the scope of the area is clear. No need to split the area into two columns unless you add a separate “Preview” or “Last run status” panel on the right (then 60% prompts, 40% panel).

5. **Publish**  
   Keep [Publish] [Stop] as they are. Optionally show “Prompts: N” next to the Publish button so the user sees how many prompts will be sent.

6. **Upscale/Vary — Count and checkboxes**  
   Do not use a full-width number input for Count. Put Count and the four checkboxes on one row: e.g. “Count:” plus a narrow number input (about 15–20% width or a column ratio like [1, 4] so the input is narrow), then the four checkboxes (Upscale Subtle, Upscale Creative, Vary Subtle, Vary Strong) in the remaining columns. Then the next row: [Run] [Stop]. So Count is a small numeric field, not a full-width block.

7. **Download — Count**  
   Same idea: Count in a narrow column (e.g. 15–25% width), then [Download] [Stop] on the same row. One row: “Download count: [narrow number] [Download] [Stop].”

8. **Gallery — actions**  
   Split the many actions into two rows so the bar is easier to scan:  
   - **Row 1:** Folder/design name or title, [Open folder], [Save design].  
   - **Row 2:** [Analyze], [Select all], [Deselect all], [Delete selected], [Delete all].  
   If you prefer one row, shorten labels (e.g. “Open”, “Save”, “Analyze”, “Del sel”, “Del all”) and use tooltips for full text.

9. **Quality threshold and Delete below threshold**  
   Put “Quality threshold” and the action on one row: a narrow number input (same approach as Count — small column width) and [Delete below threshold] next to it. Do not use a full-width number input. Optionally move this pair into a small expander “Bulk delete by score” so the main gallery bar is less crowded.

10. **Image grid**  
    Keep the current grid (e.g. 4 columns). On very wide screens you can use 5–6 columns with smaller thumbnails. Optionally add a “View: Grid | List” toggle where List shows compact rows (thumbnail + filename + actions) for users with many images.

**Summary for Image Generation:** Output folder + caption (and optional Open) → status line outside Prerequisites → batch actions on first line inside expander → Count (narrow) + checkboxes + Run/Stop for Upscale and Download → gallery actions in two rows (or shortened labels) → threshold (narrow) + Delete below threshold on one row.

---

## Tab 4: Canva Design

**Goal:** One-row entry for loading a design, one-row configuration, and clear status next to the main action.

1. **When no design is loaded**  
   Put the design package selector and the load action on one row: Design package selectbox in about 80% width, [Load for this tab] in about 20%. So the user chooses and loads in a single visual block without a full-width dropdown and a separate button below.

2. **System & Prerequisites**  
   Keep the combined checks in an expander. Add a one-line status outside the expander (e.g. “Ready” or “N issues – expand for details”) so the user doesn’t have to open it to know if they can run.

3. **Configuration expander**  
   Put all layout settings on one row when space allows: Page size (text input, about 25%), Margin % (narrow number input, about 15–20%), Outline height % (narrow number input, about 15–20%), Blank between (checkbox). Use columns so the number inputs are not full width. If the row wraps on narrow screens, use two rows: e.g. Page size + Margin + Outline on row 1, Blank between on row 2. Images folder can stay as read-only text or caption (same as Pinterest).

4. **Start Design Creation**  
   Keep the single [Start Design Creation] button. Add a short status line on the same row (or immediately next to it): e.g. “Ready. N images.” or “Browser not connected.” so the user knows why the button is enabled or disabled.

5. **Results summary**  
   Keep the four metrics (Total Images, Successful, Failed, Total Pages). Put the [Open in Canva] link or button on the same row as the success message (or the first row of the results) so it’s prominent.

**Summary for Canva:** Design package + Load on one row → status line outside Prerequisites → Configuration: one row (page size, margin %, outline %, blank) with narrow numbers → Start button + status line → Results with Open in Canva on first row.

---

## Tab 5: Pinterest Publishing

**Goal:** One-row load, compact configuration, and preview actions on one row with the main action.

1. **When no design is loaded**  
   Same as Canva: Design package selectbox about 80%, [Load for this tab] about 20%, on one row.

2. **System & Prerequisites**  
   Same pattern as Canva: one-line status outside the expander (“Ready” or “N issues – expand for details”). Keep the expander content as is.

3. **Configuration expander**  
   Put Board name and Images folder side by side: two columns (about 50% each). Put [Save Configuration] on the same row, right-aligned (e.g. in a third column or at the end of the row). So the whole config is one or two rows instead of three full-width blocks.

4. **Preview — title and Save modifications**  
   Put Pin title and [Save modifications] on one row: title input about 70%, button about 30%. Pin description stays full width below (or in a second row). So users who only change the title can save in one row.

5. **Preview — image grid**  
   Keep the 4-column grid and the Remove button per image. Optionally add a line above the grid: “N images to publish. [Deselect all]” so the selection count and bulk action are visible.

6. **Start Publishing**  
   Keep the [Start Publishing] button. Add a short line next to or under it: e.g. “N images selected” or a minimal checklist “Board ✓ Folder ✓ Browser ✓” so users see why the button is enabled or what’s missing.

7. **Publishing Sessions**  
   When a session is selected, put the session selector and the main actions on one row: e.g. session dropdown, [Re-run Publishing], [Delete session]. So the user doesn’t have to scroll to find Re-run or Delete. Optionally show sessions as a compact list where each row has [Load] [Re-run] [Delete] so no separate “select then open detail” step is needed.

**Summary for Pinterest:** Design package + Load on one row → status line outside Prerequisites → Config: Board + Folder in two columns, Save on same row → Preview: title + Save modifications on one row, description below → image grid with optional “N to publish” line → Start Publishing + short status/checklist → Sessions: selector + Re-run + Delete on one row (or compact list with inline actions).

---

## Tab 6: Orchestration

**Goal:** Compact pipeline steps, one-row design package and template save, and step configuration in one or two rows with narrow inputs.

1. **Template**  
   Keep the current row (template selectbox 3 cols, [Apply] 1 col). Optionally add a caption under Apply: “Current: [template name]” when a template is applied.

2. **Pipeline steps**  
   Show the step checkboxes in two columns instead of one long list. Split the list so roughly half the steps are in the left column and half in the right (e.g. Design, Image, … on the left; Canva, Pinterest, … on the right). Order remains top-to-bottom, left then right. This cuts vertical space. Alternatively, use a compact “chip” or “tag” style where each step is a clickable chip and selected steps are highlighted; ensure order is still clear (e.g. by numbering or order of selection).

3. **Design package**  
   Put the design package selectbox and [Load package] on one row: selectbox about 75%, button about 25%.

4. **Design idea (when design is in the pipeline)**  
   Keep the text_area for “Design idea” full width. Optionally add a placeholder and a character or word count (e.g. “0/500”) if there’s a limit. Keep [Generate] or the main action visible (e.g. under the area in one row with Clear if present).

5. **Step configuration expander**  
   Put Canva and Pinterest settings in one or two rows with narrow inputs:  
   - **Row 1:** Page size (e.g. 25%), Margin % (narrow, ~15%), Outline height % (narrow, ~15%), Blank between (checkbox), and Pinterest board name (e.g. 30%) — all in one row.  
   Or:  
   - **Row 1:** Page size, Margin %, Outline %, Blank between.  
   - **Row 2:** Pinterest board name (full or 50%).  
   Use the same narrow column pattern for Margin % and Outline % as on the Canva tab (no full-width number inputs).

6. **Save as custom template**  
   Put template name and save action on one row: text input “Template name” about 60%, [Save as custom template] about 40%.

7. **Run pipeline and errors**  
   Put [Run pipeline] and the status on one row: e.g. [Run pipeline] and next to it “Ready” or “N errors” (with errors in an expander “N errors – expand for details”). So the user always sees whether they can run and why the button might be disabled.

**Summary for Orchestration:** Template row unchanged (optional “Current” caption) → Pipeline steps in two columns or chips → Design package + Load on one row → Design idea full width (optional count) → Step config: one or two rows with narrow Canva numbers and board name → Template name + Save on one row → Run + status on one row, errors in expander.

---

## Tab 7: Progress

**Goal:** Reduce scroll, add a summary, and make each section (Designs, Jobs, Browser) easy to focus on.

1. **Summary line at the top**  
   Add one line at the top of the tab: e.g. “Designs: N  |  Jobs: M (K running)  |  Slots: P” so the user sees counts and running state at a glance without scrolling.

2. **Sub-tabs for the three sections**  
   Add three sub-tabs: “Designs”, “Jobs”, “Browser”. Each sub-tab shows only that section (Designs table, Jobs table, or Browser slots). This reduces scroll and gives each table full width. The summary line stays above the sub-tabs so the high-level picture is always visible.

3. **Designs section**  
   Keep the table-like layout (4 columns: Design, Images, Last image job, Status). Optionally use `st.dataframe` with a pandas DataFrame for sortability (e.g. by title or last job). If you keep the column-based layout, ensure column headers are clearly styled (e.g. bold, subtle border) so it reads as a table. For design path, truncate long paths (e.g. “…/folder_name”) with a tooltip or expander for the full path; optionally add an “Open folder” link.

4. **Jobs section**  
   Prefer a sortable table: use `st.dataframe` with columns Action, Status, Design path, Started, Finished so users can sort by date or status. If you need custom formatting (e.g. colored status), keep the column layout but add a “Sort by” dropdown. Truncate design path as above; optional “Open folder” for the path.

5. **Browser slots section**  
   Show each slot as a compact card: a bordered block with Slot name, Role, Port, Connection status, and [Test] [Launch] on one row. So each slot is one card and the actions are visible without extra columns. Keep Port as a narrow value (read-only or editable in a small field).

**Summary for Progress:** Summary line (Designs | Jobs | Slots with counts) → sub-tabs Designs | Jobs | Browser → Designs: table (optionally dataframe), truncated paths → Jobs: sortable table (dataframe) or sorted column layout → Browser: one card per slot with Test/Launch on one row.

---

## Tab 8: Config

**Goal:** Narrow port input, clear job summary, and optional split of running vs recent jobs.

1. **Current jobs**  
   Add a one-line summary on the main tab, outside the expander: e.g. “Jobs: 2 running, 5 recent.” So the user sees activity without opening the expander. Keep the expander with the full list. Optionally split into two expanders: “Running” (expanded when non-empty) and “Recent” (expandable), so running jobs are always visible when present.

2. **Browser slots**  
   Keep one expander per slot (or one card per slot). In each slot row, make the Port input narrow: use a column ratio where the port column is the smallest (e.g. 1 in [1, 2, 2, 3, 2] or about 10% width). So the port is clearly a small number (e.g. 9222), not a full-width field. Role, Label, [Test], [Launch] stay as they are. Optionally use two rows: row 1 = Role, Port, Label; row 2 = [Test] [Launch] and status message.

3. **Save and Reset**  
   Keep [Save configuration] and [Reset to defaults] on one row (e.g. [Save] primary, [Reset] secondary). Optionally show an “Unsaved changes” hint when any slot value has been edited and not saved.

**Summary for Config:** One-line job summary outside expander (optional: Running / Recent expanders) → Slot editor with narrow Port column → Save and Reset on one row (optional unsaved indicator).

---

## Cross-tab patterns (reference)

- **Narrow number inputs:** Port, Count, Margin %, Outline %, threshold — always in a small column (e.g. 15–25% or column ratio 1 in [1,4]). Never full width.
- **Input + primary button on one row:** Save as + Save, Design package + Load, Board + Save config, Template name + Save, Pin title + Save modifications.
- **Status line outside expander:** For System & Prerequisites (Canva, Pinterest, Image Gen): one line “Ready” or “N issues” so users don’t have to open to know status.
- **Two columns for two related fields:** Board name + Images folder (Pinterest), or Title + Description where both are short.
- **Actions on first line of expander:** Batch (Select all, Clear, Run, Quick run); Sessions (Re-run, Delete) next to selector.

Use this document as the single source of “what to do” per tab when implementing UI changes.
