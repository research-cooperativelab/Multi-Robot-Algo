# Honors thesis (CSULB scrbook format)

This directory contains the CSULB Honors Program thesis version of the
research, built on the `scrbook` template used by prior CSULB theses.

## Build

From this directory:

```
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

## Structure

- `main.tex` — wrapper that sets up the document class, loads the
  preamble, and `\input`s each chapter.
- `Chapters/` — one `.tex` file per required section:
  - `title.tex`, `signature.tex`, `abstract.tex`, `acknowledgments.tex`
    (front matter in CSULB order)
  - `introduction.tex`, `literature_review.tex`, `problem_formulation.tex`,
    `methodology.tex`, `results.tex`, `conclusion.tex` (body, matching
    the WRCR outline: Introduction, Literature Review, Hypothesis/Research
    Design, Methodology, Results, Conclusions)
- `ref.bib` — bibliography (ieeetr style).
- Figures are read from `../figures/`.

## What was carried over from the conference paper

The thesis reuses the four-model framework (M1/M2/M3/M4/M4*), the
Hungarian baselines, the FCR metric, and all theorems and proofs
(Lemma 1, Theorems 1–4, Corollary 1). Material that is new in the
thesis:

- An expanded Introduction with a disaster-response motivation and an
  explicit scope / contributions / organization breakdown.
- A full Literature Review chapter that structures the three literatures
  the thesis connects (competitive search, market-based coordination,
  energy-constrained / probabilistic search) and names the gap.
- A Problem Formulation chapter that states four falsifiable research
  hypotheses H1–H4 that the Results chapter then tests one-by-one.
- A Methodology chapter with a pseudocode algorithm for Model 4 / 4*.
- A Results chapter that reports each hypothesis test, the bounds
  verification, and the parameter sweeps.
- A Future Work section explicitly listing five directions (alternative
  objectives, tighter M4 bound, fleet-size scaling conjecture, relaxing
  assumptions, physical deployment).

## CSULB formatting notes still to verify before submission

- Confirm 1.5" left margin renders correctly after compile.
- Confirm chapter title pages start at 2" top margin (the template
  redefines chapter skip to 0pt; may need a per-chapter `\vspace*`).
- Confirm that Roman-numeral page numbering is applied in the front
  matter and that Arabic numerals restart at the Introduction.
- Confirm that no paragraph is right-justified (ragged2e is loaded,
  but long equations may still be flush-right).
- Update the graduation term in `title.tex`, `signature.tex`, and
  `abstract.tex` if it changes from "Spring 2026".
