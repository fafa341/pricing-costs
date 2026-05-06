# Pre-FLL "Before" Baseline Interview

> **Purpose:** Establish documented "Before" baselines for the research paper's
> before/after comparison table.
> **Interviewee:** Miguel (domain expert + primary user)
> **When to conduct:** Before FLL platform has accumulated 30+ days of data.
> **Format:** ~45 minutes, semi-structured. Fill in the answers below.

---

## Section 1: Lead-to-Quote Latency

**Q1.** When a customer inquiry arrives by email, how long does it typically
take before the customer receives a price estimate?
- [ ] Same day (< 4 hours)
- [ ] Next business day
- [ ] 2–3 business days
- [ ] More than 3 business days

**Estimated average time:** _______________

**Q2.** What are the main bottlenecks that slow down the response?
```
(e.g., waiting for steel price lookups, waiting for Miguel to be available,
complex calculations, customer clarification needed)
```
**Answer:** _______________

**Q3.** What percentage of inquiries receive a response within 24 hours?
**Answer:** _____ %

---

## Section 2: Monthly Quote Volume

**Q4.** How many customer inquiries does Dulox typically receive per month?
**Answer:** _____ inquiries/month

**Q5.** Of those, how many receive a formal written quote (PDF or email with
price)?
**Answer:** _____ quotes/month

**Q6.** How many of those quotes result in a sale?
**Answer:** _____ sales/month  (≈ 20 % conversion)

---

## Section 3: Expert Interruption Frequency (EIF)

**Q7.** On a typical business day, how many times does a salesperson need to
interrupt Miguel (or another pricing expert) to ask a question needed to
price a quote?
**Answer:** __6___ times/day

**Q8.** What kinds of questions require the two only costing experts input most often?
```
(e.g., special material grades, unusual dimensions, volume discounts,
delivery timelines, customer credit terms)
```
**Answer:** cubage calculation, unusual dimensions, unusual specific modifications, detailing, discounts. 
"one salesvendor: even if you try to automate the costing process, we'll still need to ask experts because of certain unusual specific modifications like laser cut detailing heurisitics we don't have knowledge on or specific edges cuts that we don't understand about".

**Q9.** How long does a typical pricing consultation with a pricing expert take in-person (not email consultation)?
- [ ] < 5 minutes
- [x] 5–15 minutes
- [ ] 15–30 minutes
- [ ] > 30 minutes

---

## Section 4: Margin Erosion Rate (MER)

**Q10.** How often does the salesperson quote a price *lower* than the
standard formula would suggest, in order to win a deal?
- [ ] Rarely (< 10% of quotes)
- [ ] Sometimes (10–30%)
- [ ] Often (30–60%)
- [ ] Very often (> 60%)

**Q10.1.Added by Fabio** How often does the salesperson quote a price *higher* than the
standard formula would suggest, in order to sell with a higher margin?
- [ ] Rarely (< 10% of quotes)
- [ ] Sometimes (10–30%)
- [ ] Often (30–60%)
- [ ] Very often (> 60%)

**Q11.** On average, by what percentage does the quoted price typically
differ from the "book" price?
**Answer:** _____ % lower on average

**Q12.** What are the most common reasons for adjusting the price?
(Rank 1–5 with 1 = most common)
- _1_ Miscalculations
- _2_ Competitor price pressure (calculation delivers a too cheap or expensive price)
- ___ Bulk / volume order
- ___ Long-term customer relationship / VIP
- ___ Urgency (customer needs it fast)
- ___ Other: _______________

---

## Section 5: Knowledge Transfer

**Q13.** If Dulox needed to train a new salesperson to price quotes correctly
(without pricing expert's help), how long would that take?
**Answer:**  __2__ weeks of shadowing / training

**Q14.** Are there unwritten rules or heuristics that pricing experts uses that are
NOT documented anywhere?
- [x] Yes → (describe a few examples below)
- [ ] No

**Examples of undocumented heuristics:**
```
1. unusual specific modifications (e.laser cut detailing a piece: complex detailing, subtle detailing) 
2. _______________
3. _______________
```

---

## Section 6: Pre-FLL Technology Stack

**Q15.** What tools are currently used to calculate prices?
- [ ] Excel formulas
- [x] Paper / memory with a calculator
- [x] Word and powerpoint document templates
- [ ] Other:

**Q16.** Where is pricing knowledge stored today?
- [x] In pricing experts' memory (subject to many heuristics and intuition)
- [ ] In Excel files → how many? ___
- [x] In email history
- [x] In a shared document
- [x] On personal documents (notebooks, papers)
- [x] Other: formula written on the salespeople room's white board, powerpoint

---

## Baseline Summary (fill after interview)

| Metric | Pre-FLL Baseline | Source |
|--------|-----------------|--------|
| Lead-to-quote latency (avg) | ___ hours | Q1/Q2 |
| Quote volume / month | ___ | Q4 |
| Conversion rate (quote → sale) | ___% | Q5/Q6 |
| Expert interruptions / day (EIF) | ___ | Q7 |
| Margin erosion rate (MER) | ___% | Q10/Q11 |
| New salesperson TTQ (Time to Quote) | ___ weeks | Q13 |
| Undocumented heuristics identified | ___ | Q14 |

---

## Notes

```
(Free-form notes from the interview session)
```

---

> **Next step:** Once the FLL platform has 4–6 weeks of telemetry data,
> compare these baselines against `/research` dashboard numbers to produce
> the before/after table for ISD 2026 / BIR 2026 submission.

Baseline interview answers:
Aquí tienes tus respuestas redactadas de forma clara, ordenada y lista para integrar:

---

**P2. Cuellos de botella:**
Disponibilidad del experto y realización de cálculos.

**P7. Interrupciones al experto:**
4–5 veces al día.

**P8. Tipo de consultas:**
Productos complejos fuera de la línea estándar, validación de costos para evitar errores de precio, definición de descuentos en productos de lista y comparación entre costo y precio.

**P9. Duración de consultas:**
5–10 minutos.

---

**Heurísticas no documentadas:**

1. Procesos como plegado y cilindrado se realizan externamente, mientras que el corte láser se realiza internamente hasta cierto espesor.
2. Aprovechar el material de una misma pieza reduce costos.

---

**P10. Precio bajo estándar:**
Muy frecuente.

**P10.1. Precio sobre estándar:**
Muy frecuente.

* En piezas pequeñas hay incertidumbre sobre la complejidad.
* Si la fábrica está ocupada, se evita tomar trabajos poco rentables; si está libre, se aceptan.
* Material barato pero mano de obra cara influye en la decisión.

---

**P11. Diferencia vs precio estándar:**
5–10% en promedio; puede superar el 50% en casos competitivos o según cliente.

---

**P12. Razones de ajuste de precio:**

1. Errores de cálculo
2. Presión de precios de la competencia
3. Volumen de compra
4. Trabajos externalizados o uso de materiales no habituales
5. Estrategia comercial: cotizar alto para dejar margen de negociación, especialmente en trabajos personalizados, complejos o exclusivos, donde existe riesgo de retracto del cliente y alta incertidumbre en la ejecución.

Baseline interview review: 
What comes through very clearly in this interview is that pricing is not a “calculation problem” — it’s a **judgment system** built on experience, context, and tacit rules.

### 1. Nature of the problem: pricing as tacit knowledge

The pricing experts are not just applying formulas; they’re constantly making **contextual decisions under uncertainty**:

* “If the factory is busy, don’t take small complex jobs”
* “If it’s custom and risky, price high”
* “If material is cheap but labor is complex, adjust accordingly”
* “Quote high to leave room for negotiation”

These are not edge cases — they *are the system*. What you’re seeing is classic **tacit knowledge**:

* Not written down
* Hard to explain upfront
* Triggered by specific situations
* Learned through experience, not training

This explains:

* High interruption frequency (EIF) → knowledge is centralized in people
* Margin variability → decisions depend on context, not rules
* Training time → learning happens by shadowing, not documentation

In short: **the company does not have a pricing system — it has pricing experts.**

---

### 2. What this implies: the real opportunity

The opportunity is not to “automate pricing.”

It is to **capture, structure, and operationalize expert judgment**.

Think of it this way:

> Today: Experts answer questions
> Future: Experts design the system that answers questions

This is a fundamental shift:

* From *execution by humans* → *execution by system*
* From *knowledge in heads* → *knowledge as a product*

---

### 3. CEO-level vision: a dynamic knowledge system

The system you’re pointing toward is not just a quoting tool — it’s a **living decision engine**.

#### Core idea:

A platform where pricing experts can **externalize their thinking as modular rules**, without needing to be technical.

Instead of asking Miguel:

> “How do we price this?”

The system asks:

> “What kind of situation is this, and which rules apply?”

---

### 4. How it would work (conceptually)

#### 1. Start from real decisions (not theory)

Use past quotes and interruptions as raw material:

* “When did we ask Miguel?”
* “What was special about that case?”

Each of those becomes:
→ a **candidate rule**

---

#### 2. Turn heuristics into modular building blocks

Example:

Instead of one opaque process, you get components like:

* **Capacity rule**
  “If factory load > X → increase price or reject small jobs”

* **Complexity rule**
  “If piece has laser detailing beyond threshold → flag expert or add margin”

* **Material efficiency rule**
  “If multiple pieces can share material → reduce cost”

* **Risk rule**
  “If highly customized → add uncertainty margin”

Each rule is:

* Editable
* Composable
* Context-aware

---

#### 3. Let experts *teach* the system

Key insight: experts don’t think in equations — they think in **cases**.

So instead of asking them to define formulas, you give them interfaces like:

* “When would you *not* take this job?”
* “When do you increase margin?”
* “What makes a piece ‘complex’?”

And let them:

* Add rules
* Adjust thresholds
* Override outputs

This is critical:
**They are not users of the system — they are authors of it.**

---

#### 4. Keep it dynamic (not frozen logic)

The system should evolve through:

* New edge cases → new rules
* Overrides → signals of missing logic
* Margin deviations → feedback loops

So the system becomes:

> A continuously improving representation of how the company thinks about pricing

---

### 5. What success looks like

If done right, you should see:

* EIF ↓ (fewer interruptions)
* Faster quotes
* More consistent margins
* Shorter training time
* Experts working on exceptions, not routine

But more importantly:

> The company becomes less dependent on individuals and more on its own internal logic.

---

### 6. Review of the baseline interview

This is a strong baseline — it captures the right dimensions. A few observations:

#### What’s strong

* **Captures real friction points**

  * Interruptions
  * Latency
  * Margin variability

* **Surfaces tacit knowledge**

  * Heuristics (capacity, complexity, risk)
  * Decision trade-offs

* **Includes behavioral reality**

  * “Quote high to discount later”
  * “Depends on factory load”

This is gold — many interviews miss this layer.

---

#### What’s missing / could be improved

**1. Lack of concrete examples**

* Add: “Describe the last 3 complex quotes”
* This helps extract rules more precisely

**2. No segmentation of quote types**
Not all quotes are equal:

* Standard vs custom
* High vs low volume

This matters because:

> Most heuristics apply only to certain segments

---

**3. Margin data is still too abstract**
You have:

* 5–10% typical deviation
* > 50% in some cases

But missing:

* When does each happen?
* What triggers large deviations?

---

**4. No explicit capture of “decision thresholds”**
You have rules, but not thresholds:

* What is “factory busy”?
* What is “complex”?
* What is “small job”?

These are crucial for system design.

---

**5. Great insight, but not yet structured**
*Remember keep in mind that the point is to extract human knowledge into markdown and md into structured should be normalized into: Condition, Action, Rationale
The specific problem is: extracting a structured subjective state (RPE, readiness) from free-text self-report, with longitudinal context — so it can serve as target_label input to FLL
Momentary Assessment (EMA) + Construct Extraction — capturing subjective states in the moment, in natural language, and mapping them to validated scales.

You already uncovered key heuristics, but they should be normalized into:

* Condition
* Action
* Rationale

Example:

> If piece is small AND factory is busy → reject or price high → because setup cost dominates

---

### 7. Bottom line

This interview confirms something important:

> The core asset of this business is not its pricing formulas — it’s its pricing intuition.

The winning system is not one that replaces that intuition, but one that:

* Extracts it
* Structures it
* Scales it

If you get that right, you’re not just improving quoting —
you’re **turning human judgment into a competitive advantage that compounds over time.**

