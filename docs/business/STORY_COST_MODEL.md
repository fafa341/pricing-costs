# The Cost Model Story
## A Storytelling Brief for Blog + Illustrations

> **Purpose:** This document is a structured narrative brief to be fed to an AI writing assistant. It captures the full arc of the story — the problem, the model, and the human-computer challenge — with section-by-section framing, illustration prompts, and voice notes. The goal is a long-form blog post that is intellectually honest, technically rich, and emotionally resonant for an audience of builders, founders, and engineers.

---

## NARRATIVE ARC OVERVIEW

```
ACT 1 — The Problem        They've been flying blind for 30 years.
ACT 2 — The Insight        You can't price what you can't decompose.
ACT 3 — The Model          4 drivers × 11 processes × 3 complexity tiers.
ACT 4 — The Hard Part      The knowledge lives inside one person's head.
ACT 5 — The Ingestion Loop Intercept the sketch. Decode the expert.
ACT 6 — The Philosophy     AI as augmentation. Human as source of truth.
```

**Tone:** Direct, grounded, first-person. Builder telling the truth about a messy problem. Not academic, not startup-pitchy. The reader should feel like they're watching someone think in real time.

**Audience:** Engineers, product people, and founders who've wrestled with "how do we actually capture expert knowledge." Industrial context, but the real subject is epistemology and human-computer interaction.

---

## SECTION 1 — The Factory That Prices Products Out of Thin Air

**Story beat:** Establish the company and the core absurdity of the situation.

**What to convey:**
- Ingeniería en Aceros (Dulox) is a Chilean stainless steel manufacturer. They make custom products — everything from industrial kitchen counters to custom trash bins to campanas for restaurants.
- Two product lines: small batch standard products, and fully custom one-off projects for clients.
- Every product is different. Different dimensions, different processes, different complexity.
- For years, their pricing method has been: cost of materials × a factor. That factor is meant to absorb all factory overhead — operators, machines, time, consumables — spread uniformly across everything.
- The problem: that factor treats a simple shelf the same as a complex cylindrical trash bin with interior welds and mirror polish. They are not the same. Not even close.

**The core absurdity (write this out):**
> They've been profitable for years. So the factor works — on average. The factory makes money overall. But they have no idea which products make money and which ones don't. They don't know what to prioritize. They can't quote competitively because they don't know their real costs. And when the salesperson quotes a complex product too low, nobody catches it until the order is halfway through production.

**Illustration idea:** A single factory worker at a machine, with a price tag floating above. The price tag is a question mark. Around the room: different products at different complexity levels, all with the same question mark price tag.

**Key question to plant in the reader's mind:** *What does it actually cost to make this specific thing?*

---

## SECTION 2 — The Real Problem Is Decomposition

**Story beat:** The insight that changes the frame. This isn't a pricing problem. It's a decomposition problem.

**What to convey:**
- Before you can price something, you have to be able to decompose it — break it into its cost primitives.
- For a stainless steel product, the cost primitives are: materials, direct labor per process, machine time, consumables.
- The reason the factor has worked is that nobody had done this decomposition. It's hard. It requires sitting with the production manager and actually mapping out what happens to a product from steel sheet to finished piece.
- The real challenge: every product is custom, so you can't have a fixed price list. You need a model that generalizes — that can take any new product and estimate cost without having measured it before.

**The structural decision:**
> The answer is: classify products into profiles (what processes they go through) and complexity tiers (how hard each process is). If you know both, you can compute cost. If you can generalize both to new products, you have a pricing engine.

**Illustration idea:** A product exploded into its constituent processes. Each process has a cost. The sum is the real cost. This is the decomposition.

---

## SECTION 3 — Categories: What a Product IS Determines What It Costs

**Story beat:** Introduce product categorization as the foundation of the model.

**What to convey:**
- First step: go through all 1,300+ SKUs and classify each one into a `perfil_proceso` — a process profile.
- A process profile says: *this type of product goes through these specific manufacturing processes.*
- Examples: a cylindrical trash bin profile activates: trazado, corte, cilindrado, soldadura, pulido, QC. A flat shelf activates: trazado, corte, plegado, soldadura, QC. Different routes through the factory.
- This is not a product category in the commercial sense. It's a manufacturing identity. Two products that look nothing alike can share a profile if they go through the same factory processes.
- The categorization work itself was painstaking: reviewing hundreds of past products, building the logic for what profile each belongs to.

**The decision that mattered:** 
> It would have been easy to make dozens of micro-categories. We resisted. The goal was the smallest number of profiles that still captures real cost variation. Too many profiles and the model becomes unmaintainable. Too few and it loses resolution.

**Illustration idea:** A grid of stainless steel products. Arrows group them into 5-7 clusters. Each cluster = a process profile. The grouping is not by shape or appearance, but by what happens to them in the factory.

---

## SECTION 4 — Four Numbers That Explain Complexity

**Story beat:** The heart of the model. The four universal drivers.

**What to convey:**
- Once you know the profile (which processes), you still need to know the complexity (how hard each process is for this specific product).
- The insight: instead of asking "how complex is this product overall," ask "what are the physical parameters that drive difficulty in manufacturing?"
- We landed on four universal drivers, each scored 1-3:

**G — Geometry (surface area)**
> The amount of steel the product consumes. Larger products require more cutting, more welding, more polishing, more material. Surface area is the most direct proxy for scale.

**D — Density (material thickness)**
> A 1mm product is not the same as a 5mm product. Thicker steel is harder to cut, harder to bend, requires more powerful machines, demands more skilled operators. It also changes the profile of consumables (welding wire, argon, blade wear).

**C — Components (part count)**
> A product with 4 components versus 12 components is fundamentally different in assembly complexity. More components = more joints = more welding, more fit-up, more chances for dimensional error.

**X — Expert Variables (complexity flags)**
> Everything the operators know intuitively that doesn't fit neatly into geometry, density, or count. Examples: Is it a hollow product you have to weld from the inside? Does it have a mirror-polish finish? Does it have a logo or etching? Is it designed to refrigerate? These are binary flags that add points to the system. They are the formalization of 30 years of intuition.

**How the drivers feed the model:**
> Each process uses a subset of the four drivers. Welding uses C and X. Polishing uses G and X. Bending uses G, D, and C. Each combination gives a score. That score maps to a complexity tier: C1 (standard), C2 (elevated), C3 (expert). Each tier has calibrated time estimates derived from real production measurements.

**Illustration idea:** A 2×2 driver grid. Each quadrant shows an example: large vs small (G), thick vs thin (D), few vs many parts (C), standard vs flagged product (X). Below: how these combine to give a process its complexity tier.

---

## SECTION 5 — Eleven Processes, Three Tiers Each

**Story beat:** Make the model concrete. Show how a product becomes a number.

**What to convey:**
- There are 11 manufacturing processes that cover everything Dulox does: trazado, corte manual, corte láser, grabado láser, plegado, cilindrado, soldadura, pulido, pintura, refrigeración, QC.
- Each process, for each product, gets assigned C1, C2, or C3.
- Each tier has a calibrated time estimate (in minutes), operator count, and consumable package. These come from direct production measurement — a chronometer session with the production manager.
- The cost per process = (time × operator rate) + machine depreciation + consumables.
- The total product cost = sum across all active processes.

**The extrapolation problem:**
> You can't measure every product. There are 1,300 SKUs. So you calibrate on 7 anchor products — the most common, covering the widest range of processes and complexity — and then extrapolate to everything else. A new product is assigned to the nearest anchor by process profile, and its dimensions scale the time estimates proportionally.

**Illustration idea:** A table with 11 rows (processes) and 3 columns (C1/C2/C3). For each cell: time in minutes and cost in CLP. This is the pricing engine made visible.

---

## SECTION 6 — The Knowledge Problem: It Lives in One Person's Head

**Story beat:** The real challenge. This is where the story gets human.

**What to convey:**
- The production manager — Hernán — has been working at Dulox for over 30 years. He knows, intuitively, how long every process takes. He knows which products are going to be trouble before they're even started. He knows which operators can handle which complexity.
- This knowledge is real, it's accurate, and it is completely informal. It exists only in his head.
- The challenge: how do you extract, formalize, and make consistent something that someone has never had to articulate?
- You can't just interview him once. The knowledge is contextual, process-specific, and changes as machines change, operators learn, and new product types appear.
- The first sessions with Hernán were hard. He would say things like "that takes about 40 minutes" and when you asked "for what size piece?" he'd think for a second and say "well, it depends." The job was to make the "it depends" explicit.

**The deeper problem:**
> Formalization changes things. When you ask an expert to articulate their knowledge, they often realize they don't know it as precisely as they thought. The process of articulation creates new clarity — and reveals new uncertainty. This is uncomfortable. The expert feels exposed. The interviewer has to be careful not to undermine the trust that makes the extraction possible.

**Illustration idea:** A brain with gears. Knowledge flowing out as structured data. But the flow is partial — some knowledge resists formalization, some is ambiguous, some doesn't make sense until a second interview two weeks later.

---

## SECTION 7 — Intercepting the Existing Workflow

**Story beat:** The ingestion solution. Don't change behavior, intercept it.

**What to convey:**
- The failure mode of most "digitization" projects: you ask people to do new things. New forms, new software, new habits. The resistance is enormous. These are people who've been doing this for 15 years. Every new step is friction. Friction becomes abandonment.
- The insight: don't change the workflow. Find the existing artifact that already captures the information you need, and build the system around that artifact.
- What already exists: when a production order arrives, Hernán draws a sketch. He's always drawn sketches. The sketch goes to each operator with annotations. It's his primary communication tool.
- The sketch contains: dimensions, material specifications, process indications, complexity flags, special notes for operators. Everything we need.

**The ingestion loop:**
> The sketch is photographed. The photograph is processed by a vision model trained to extract the structured data in the Dulox schema. The output is a JSON that feeds directly into the cost model. The production manager reviews and confirms. The model updates.

**Why this matters:**
> We didn't ask Hernán to learn software. We didn't ask him to fill forms. We asked him to keep doing exactly what he already does — draw his sketch — and we built the computer system around his native output. His friction is zero. The system's data is rich.

**Illustration idea:** Hernán drawing a sketch on paper → phone camera → vision model → structured JSON → cost output. The human is in the center, unchanged. The technology wraps around him.

---

## SECTION 8 — The Philosophy: Augmentation, Not Replacement

**Story beat:** Zoom out. The real thesis of the project.

**What to convey:**
- The easy version of this story is: "we used AI to price products." That misses the point entirely.
- The AI (vision model, classification model) is not the innovation. The innovation is the epistemological work: making the implicit explicit, structuring what was intuitive, building a system that can hold and communicate expert knowledge consistently.
- The production manager is not being replaced. He is being equipped with a mirror — a system that reflects his own knowledge back to him in a form that can be shared, challenged, updated, and improved.
- When the model is wrong (and it will be, especially early), Hernán corrects it. The correction teaches the model. The model becomes more accurate. Hernán becomes more consistent because he has to articulate the exception.
- This is a feedback loop between human expertise and machine structure. Neither works without the other.

**The deeper claim:**
> The most valuable application of AI in manufacturing is not automation of tasks. It's the formalization of expertise. The 30-year veteran who retires takes his knowledge with him. If you've built the system, the knowledge stays.

**The honest caveat:**
> This is hard. It takes longer than you expect. The expert has to trust you. The organization has to commit to maintaining the model. The data quality depends on human diligence. There is no version of this that runs itself.

**Illustration idea:** A scale. On one side: the expert's brain (human, informal, decades of experience). On the other side: the cost model (structured, queryable, shareable). A bridge between them, built from the sketch and the interview. Both sides need the other to function.

---

## CLOSING — What Changes When You Can Actually See

**Story beat:** What happens when the model works?

**What to convey:**
- Salespeople can now quote with confidence. Not just "the factor says X" but "this product has this profile, this complexity, and this is why."
- The company can see margin by product type for the first time. They can identify which categories are systematically underpriced and which have room to expand.
- The production manager's knowledge is no longer locked in his head. Junior people can consult the system. Onboarding becomes faster.
- When a new product type comes in, the system gives a starting estimate instead of a blank page. The expert reviews and refines, but the baseline is no longer zero.
- Most importantly: the company can compete. They can price confidently at market rates without fearing they're leaving money on the table or taking losses on complex orders.

**Final line (draft):**
> The factory didn't change. The machines are the same. The operators are the same. Hernán still draws his sketches every morning. What changed is that now, when the sketch is done, the number is right.

---

## ILLUSTRATION BRIEF (consolidated)

| Section | Image concept |
|---------|---------------|
| 1 | Factory floor, all products with "?" price tags. Same factor applied to everything. |
| 2 | One product exploded into labeled cost primitives. The sum becomes the real price. |
| 3 | Product grid regrouped by process profile, not appearance. |
| 4 | Four driver dials: G (area), D (thickness), C (components), X (flags). Scores combine into complexity. |
| 5 | 11-process × 3-tier cost table. A product's active cells light up and sum to total cost. |
| 6 | Expert brain → interview → partial formalization. Some knowledge resists. |
| 7 | Sketch → camera → vision model → JSON → cost. The human unchanged at center. |
| 8 | Scale: human expertise vs machine structure. Bridge = sketch + interview. |
| Closing | A single correct number next to a sketch. Simple. Earned. |

---

## VOICE NOTES FOR THE WRITER

- Write from first person. "I" not "the team."
- Don't soften the problems. The factory had real gaps. The expert sessions were uncomfortable. The model was wrong before it was right. Show the friction.
- Technical depth is welcome but must serve the narrative. Every equation or structure should be followed immediately by what it means in plain language.
- The audience should feel smart for understanding, not excluded for not knowing manufacturing.
- Avoid: "AI-powered," "data-driven," "game-changing," "revolutionary." These are noise.
- The emotional core: there's something beautiful about taking 30 years of expertise and making it visible, shareable, and legible for the first time. That's the feeling to leave the reader with.
- Suggested length for full blog post: 3,000–4,500 words. This document is the scaffold — the writer fills the flesh.
