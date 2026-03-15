# Workflow: Running 5 Designs and Parallelisation Options

This doc explains how to run **5 designs** and where the app **parallelises** vs runs **sequentially**.

---

## 1. Where parallelisation happens today

| Stage | What runs in parallel | What runs sequentially |
|--------|------------------------|-------------------------|
| **Design Generation** | **Yes.** When you use **Generate All N Designs**, up to **4 designs** are generated at the same time (thread pool). For 5 designs: 4 run in parallel, then the 5th. You can switch tabs while it runs (background). | Direct path (“Describe your coloring book”) generates **one** design at a time (blocking). |
| **Image Generation (Midjourney)** | **No.** One browser, one design at a time. Inside a **single** design: prompts are sent in batches (e.g. 10), but the pipeline (Publish → Upscale/Vary → Download) is one flow per design. | **Batch mode** runs **5 designs one after the other**: Design 1 full pipeline, then Design 2, then 3, 4, 5. Same browser, sequential. |
| **Evaluation** | **No.** One folder (one design) at a time. | Per-design, sequential if you run multiple. |
| **Canva** | **No.** One design per “Start Design Creation”. | One design per run. |
| **Pinterest** | **No.** One design per “Start Publishing”. | One design per run. |
| **Orchestration pipeline** | **No.** One design per pipeline run. | Steps (design → image → evaluate → canva → pinterest) run in order for **one** design. |

So the **only** parallelisation in the app is: **Design Generation “Generate All”** (up to 4 designs at once). Everything else is either one-at-a-time or sequential batch.

---

## 2. Recommended workflow for 5 designs (max parallelisation)

Goal: create **5 design packages** and parallelise as much as possible.

### Step A: Create 5 designs in parallel (Design Generation tab)

1. Open **Design Generation**.
2. **Concept path:** Enter an idea (e.g. “forest animals for adults”) → click **Generate N Concept Variations** (e.g. 5).
3. Add 5 concepts to the list (e.g. **Add all variations** or pick 5 manually). You can have up to 10 selected (app limit).
4. Click **Generate All 5 Designs**.
5. The app runs **4 designs in parallel**, then the 5th (background). You can switch to other tabs; click **Refresh** in Design Gen to see when all 5 are done.
6. Each design is saved as a **design package** (folder with prompts, title, etc.). The list “Concept 1”, “Concept 2”, … shows them. You can **Use this design** to load one into the rest of the app.

Result: **5 design packages** with minimal wall‑clock time (parallel design gen).

### Step B: Image generation for all 5 designs (sequential)

You have two ways to run images for all 5:

**Option B1 – Batch in Image Generation (one flow, sequential)**

1. Open **Image Generation**.
2. Ensure the **design list** includes your 5 packages (they appear from Step A as “generated” designs, plus any saved packages).
3. Expand **Run multiple designs (batch)**.
4. **Select all** (or tick the 5 designs you want).
5. Click **Run** (or **Quick run** if you use that variant).
6. The app runs **Design 1** (Publish → Upscale/Vary → Download) in its own subfolder, then **Design 2**, …, then **Design 5**. **One browser, one design at a time** – sequential.
7. Each design’s images go into its **own subfolder** under the output structure.

**Option B2 – Manual, one design at a time**

1. In **Design Generation**, click **Use this design** for Design 1 → it becomes the current design (sidebar + Image Gen).
2. In **Image Generation**, set output folder, run Publish → Upscale/Vary → Download for that one design.
3. Repeat for Design 2, 3, 4, 5 (load each in turn, run image pipeline).

B1 is less manual; B2 gives you full control per design. Neither runs image gen for 5 designs in parallel (single Midjourney browser).

### Step C: Canva / Pinterest (one design at a time)

- **Canva:** Load one design (from sidebar or design selector in Canva tab), run **Start Design Creation**. Repeat for each of the 5 when you’re ready.
- **Pinterest:** Same idea – load one design, run **Start Publishing** for that design’s images. Repeat for the other 4.

No built-in batch; you run each design separately. You can use different browser slots (e.g. Canva on one port, Pinterest on another) so that **Canva for one design** and **Pinterest for another** are not blocking each other’s browser, but each action is still one design per run.

---

## 3. Orchestration tab and 5 designs

The **Orchestration** pipeline (templates like “Design to Images” or “Full Pipeline”) runs **one design per run**:

- If you include the **Design** step, it creates **one** design from your idea, then runs image / evaluate / canva / pinterest for that design.
- If you **don’t** include Design, you must **choose one design package**; the pipeline runs image → … → pinterest for that single design.

So Orchestration does **not** run 5 designs in one go. To get 5 designs through the pipeline you either:

- Run the pipeline **5 times**, changing the selected design package each time, or  
- Use **Design Gen “Generate All 5”** (parallel) then **Image Gen batch** (sequential) as in Section 2, and use Canva/Pinterest per design as needed.

---

## 4. Summary: options for 5 designs

| Goal | Option | Parallel? |
|------|--------|-----------|
| **Create 5 design packages** | Design Gen → concept variations → select 5 → **Generate All 5 Designs** | **Yes** (up to 4 at a time; 5th after). |
| **Generate images for 5 designs** | Image Gen → **Run multiple designs (batch)** → select 5 → Run | **No** (sequential: design 1, then 2, …, then 5). |
| **Run full pipeline (design → images → …) for 5 designs** | Not in one click. Use Design Gen (parallel) for 5 packages, then Image Gen batch (sequential), then Canva/Pinterest per design. | Design gen **yes**; image/canva/pinterest **no**. |
| **Run 5 image generations in parallel** | Not supported. One Midjourney browser; batch is sequential. Would require multiple browsers and code changes. | **No.** |

So for a user aiming to **run 5 designs and parallelise as much as possible**:

- **Best option:** Use **Design Generation “Generate All 5 Designs”** to create 5 packages in parallel (4+1). Then use **Image Generation “Run multiple designs (batch)”** to process all 5 **sequentially** in one go. Canva and Pinterest stay one design per run; you can interleave them with other work (e.g. different browser tabs/slots) but the app does not batch them.
