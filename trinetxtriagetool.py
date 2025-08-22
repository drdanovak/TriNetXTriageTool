# We'll create a Streamlit app file and a requirements.txt for the user to download.
from textwrap import dedent
from pathlib import Path

app_code = dedent(r'''
# TriNetX Study Triage + STROBE Planner
# Author: ChatGPT (for Daniel Novak)
# Run with: streamlit run triage_strobe_app.py

import json
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# ----------------------------
# App Config & Styling
# ----------------------------
st.set_page_config(
    page_title="TriNetX Triage + STROBE Planner",
    page_icon="🧭",
    layout="wide",
)

HIDE_FOOTER = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: visible;}
/* Make form sections stand out */
.block-container {padding-top: 1rem; padding-bottom: 4rem;}
section[data-testid="stSidebar"] {width: 360px !important;}
</style>
"""
st.markdown(HIDE_FOOTER, unsafe_allow_html=True)

# ----------------------------
# Utility Data
# ----------------------------

TRIAGE_DOMAINS = [
    ("A. Novelty & significance", "Is there a clear, non-trivial contribution or gap addressed?"),
    ("B. Mechanistic/clinical rationale", "Is there a plausible clinical/biological rationale with citations?"),
    ("C. Cohort fidelity", "Are codes specific, validated/peer-anchored, with appropriate washout/indexing?"),
    ("D. Exposure definition", "Is there a new-user/active-comparator design, dose/duration captured?"),
    ("E. Outcome validity", "Is the outcome specific, temporally aligned, and preferably validated/triangulated?"),
    ("F. Confounding control", "Is there strong adjustment (PSM/IPTW), SMD<0.1, diagnostics shown?"),
    ("G. Bias handling", "Are immortal time/time-lag/misattribution addressed in design/analysis?"),
    ("H. Analytic depth", "More than one model; sensitivity/heterogeneity pre-specified?"),
    ("I. Robustness", "Negative controls/falsification; E-value/tipping-point; alternative specs?"),
    ("J. Generalizability", "Is scope/population clear; multi-site; equity lens when relevant?"),
    ("K. Reproducibility", "Provenance: saved queries, code lists, versions, date-stamps?"),
    ("L. Visuals & reporting", "Cohort diagram, balance plots, survival/cum. incidence, forest figures?"),
]

DEPTH_UPGRADES = [
    "Redesign to new-user with active comparator",
    "Tighten washout/index; add grace periods for exposure gaps",
    "Full covariate balance plots + overlap histograms",
    "PH assumption checks or flexible hazards (e.g., Aalen, time-varying covariates)",
    "Competing risks (Fine–Gray) when appropriate",
    "Falsification endpoints or negative exposure controls",
    "E-value or tipping-point for unmeasured confounding",
    "Pre-specified subgroups/interaction (sex, age, comorbidity)",
    "Equity moderators (URIM, FirstGen, site access) when justified",
    "Calendar-time or pandemic-era sensitivity analyses",
    "Triangulate outcome definitions (strict vs. broad)",
    "Replicate with alternate adjustment (IPTW vs. PSM)",
    "Dose–response or time-on-treatment analysis",
    "Journal-ready figures: flow, balance, KM/CIF, forest",
]

# STROBE items (base core + design-specific addenda)
# Each item: (id, section_label, prompt)
STROBE_BASE = [
    ("ST1", "Title/Abstract", "Indicate the study design with a commonly used term in the title or the abstract."),
    ("ST2", "Title/Abstract", "Provide an informative and balanced summary of what was done and found."),
    ("ST3", "Introduction", "Explain the scientific background and rationale for the investigation."),
    ("ST4", "Introduction", "State specific objectives, including any pre-specified hypotheses."),
    ("ST5", "Methods", "Present key elements of study design early in the paper."),
    ("ST6", "Methods", "Describe the setting, locations, and relevant dates, including periods of recruitment, exposure, follow-up, and data collection."),
    ("ST7", "Methods", "Give the eligibility criteria, and the sources and methods of participant selection."),
    ("ST8", "Methods", "Clearly define all outcomes, exposures, predictors, potential confounders, and effect modifiers."),
    ("ST9", "Methods", "For each variable of interest, give sources of data and details of methods of assessment."),
    ("ST10","Methods", "Describe any efforts to address potential sources of bias."),
    ("ST11","Methods", "Explain how the study size was arrived at (power/precision)."),
    ("ST12","Methods", "Explain how quantitative variables were handled in the analyses (e.g., groupings, transformations)."),
    ("ST13","Methods", "Describe all statistical methods, including confounding control; describe methods to examine subgroups and interactions."),
    ("ST14","Methods", "Explain how missing data were addressed."),
    ("ST15","Results", "Report the numbers of individuals at each stage of the study (e.g., eligibility, included, follow-up, analysis); give reasons for non-participation; consider a flow diagram."),
    ("ST16","Results", "Give characteristics of study participants and information on exposures and potential confounders."),
    ("ST17","Results", "Report numbers of outcome events or summary measures over time."),
    ("ST18","Results", "Give unadjusted estimates and, if applicable, confounder-adjusted estimates and their precision (e.g., 95% CI)."),
    ("ST19","Results", "Report category boundaries when continuous variables were categorized; consider translating relative risk into absolute risk."),
    ("ST20","Results", "Report other analyses done—e.g., subgroup and interaction analyses, and sensitivity analyses."),
    ("ST21","Discussion", "Summarise key results with reference to study objectives."),
    ("ST22","Discussion", "Discuss limitations, considering sources of bias or imprecision; discuss direction and magnitude of potential bias."),
    ("ST23","Discussion", "Provide a cautious overall interpretation considering objectives, limitations, multiplicity, and other relevant evidence."),
    ("ST24","Discussion", "Discuss the generalisability (external validity) of the study results."),
    ("ST25","Other Information", "Give the source of funding and the role of the funders, if any."),
]

# Design-specific additions/clarifiers
STROBE_COHORT = [
    ("STC1","Methods","For matched cohort studies, give matching criteria and numbers of exposed and unexposed."),
    ("STC2","Results","Report follow-up time (e.g., average and total amount)."),
    ("STC3","Results","Describe loss to follow-up and how it was addressed."),
]

STROBE_CASECONTROL = [
    ("STCC1","Methods","Give the eligibility criteria for cases and controls and the sources and methods of case ascertainment and control selection."),
    ("STCC2","Methods","For matched case–control studies, give matching criteria and the number of controls per case."),
    ("STCC3","Results","Report numbers in each exposure category and provide a summary of exposure measures."),
]

STROBE_CROSSSECTIONAL = [
    ("STXS1","Methods","Describe how participants were selected (e.g., random sampling, consecutive)."),
]

# Gate A (fatal flaws)
GATE_A_ITEMS = [
    ("Q1", "Clear clinical question with explicit comparison and outcome?"),
    ("Q2", "Cohort definition unambiguous (codes validated/peer-anchored) with index and washout defined?"),
    ("Q3", "Credible sample size for outcomes (or provide power/precision justification)?"),
    ("Q4", "Confounding strategy fit to question (PSM/IPTW/stratification/time-to-event)?"),
    ("Q5", "Bias traps addressed: immortal time, time-lag, prevalent-user, misclassification, differential follow-up?"),
    ("Q6", "Outcome ascertainment specific and temporally aligned to index?"),
]

# Gate B (minimum standards by design)
GATE_B_MIN = {
    "Cohort": [
        "New-user design or explicit rationale for prevalent users.",
        "Active comparator (if feasible) and index date alignment.",
        "Pre-specified covariates; balance table with SMD<0.10 post-adjustment.",
        "Proportional hazards checked if using Cox; censoring rules transparent.",
    ],
    "Case–control": [
        "Clear case definition; control selection free of outcome; matching criteria (if any) described.",
        "Exposure assessment window defined relative to index; blinding of exposure assessment if feasible.",
        "Confounding addressed via matching/stratification/regression/PS; diagnostics provided.",
    ],
    "Cross-sectional": [
        "Sampling strategy described; weights if applicable.",
        "Measurement validity for exposure/outcome; temporality caveats stated.",
        "Confounding and collinearity considered; appropriate regression/robust SEs.",
    ],
}

# ----------------------------
# Helper Functions
# ----------------------------

def strobe_items_for_design(design: str) -> List[Tuple[str,str,str]]:
    base = STROBE_BASE.copy()
    if design == "Cohort":
        return base + STROBE_COHORT
    elif design == "Case–control":
        return base + STROBE_CASECONTROL
    elif design == "Cross-sectional":
        return base + STROBE_CROSSSECTIONAL
    else:
        return base

def compute_strobe_score(checks: Dict[str, Dict]) -> Tuple[int, int, float]:
    total = len(checks)
    yes = sum(1 for v in checks.values() if v.get("addressed", False))
    pct = (yes / total * 100.0) if total else 0.0
    return yes, total, pct

def triage_decision(rubric_total: int, strobe_pct: float, gates_pass: bool) -> Tuple[str, str]:
    if not gates_pass:
        return ("Refactor or Poster", "Gate A failed: fix design fundamentals before proceeding.")
    if rubric_total >= 20 and strobe_pct >= 80:
        return ("Full Manuscript", "Strong project with adequate reporting. Proceed to journal targeting.")
    if rubric_total >= 16 and strobe_pct >= 70:
        return ("Brief Report / Short Communication", "Solid core; add 1–2 depth upgrades and ensure STROBE polish.")
    if rubric_total >= 12:
        return ("Abstract / Poster", "Viable for meeting; consider depth upgrades and STROBE completeness to escalate.")
    return ("Refactor or Educational Poster", "Scope down or re-design. Use as learning vehicle.")

def make_report_md(state: Dict) -> str:
    yes, total, pct = compute_strobe_score(state["strobe_checks"])
    decision, rationale = triage_decision(state["rubric_total"], pct, state["gates_pass"])

    # Summaries
    gate_a_summary = "\n".join([f"- [{'x' if v else ' '}] {label}" for key, label in GATE_A_ITEMS for v in [state['gate_a'][key]]])
    gate_b_summary = "\n".join([f"- [{'x' if state['gate_b'][i] else ' '}] {i}" for i in state["gate_b_items"]])

    rubric_lines = []
    for (dom, desc) in TRIAGE_DOMAINS:
        score = state["rubric"].get(dom, 0)
        rubric_lines.append(f"| {dom} | {score} | {desc} |")
    rubric_table = "\n".join(["| Domain | Score | Notes |","|---|---:|---|"] + rubric_lines)

    strobe_table_rows = []
    for k, v in state["strobe_checks"].items():
        strobe_table_rows.append(f"| {k} | {'Yes' if v.get('addressed') else 'No'} | {v.get('where','')} |")
    strobe_table = "\n".join(["| STROBE Item | Addressed | Where/How |","|---|---|---|"] + strobe_table_rows)

    upgrades = state.get("upgrades", [])
    upgrades_list = "\n".join([f"- {u}" for u in upgrades]) if upgrades else "- (none selected)"

    md = f"""# TriNetX Triage + STROBE Report

**Generated:** {datetime.now().isoformat(timespec='seconds')}

## Project Basics
- **Title:** {state.get('title','')}
- **Clinical Question (PECO/PECOS):** {state.get('question','')}
- **Design:** {state.get('design','')}
- **Index Date:** {state.get('index','')}
- **Data Period:** {state.get('period','')}
- **Sites:** {state.get('sites','')}
- **IRB/Privacy:** {state.get('irb','')}

---

## Gate A — Fatal Flaws
{gate_a_summary}

## Gate B — Minimum Standards ({state.get('design','')})
{gate_b_summary}

---

## STROBE Checklist Completion
- **Completed:** {yes}/{total} ({pct:.1f}%)

{strobe_table}

---

## Scored Triage Rubric (max 24)
**Total:** {state["rubric_total"]}/24

{rubric_table}

---

## Depth Upgrade Selections
{upgrades_list}

---

## Decision
- **Recommended Track:** **{decision}**
- **Rationale:** {rationale}

---

## Next Steps
- Close any remaining Gate A/B gaps.
- Improve STROBE items marked "No".
- Implement selected depth upgrades.
- Finalize figures: cohort flow, balance, KM/CIF, forest as applicable.
"""

    return md

def init_state():
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True
    st.session_state.gate_a = {k: False for k, _ in GATE_A_ITEMS}
    st.session_state.gate_b = {}
    st.session_state.rubric = {dom: 0 for dom, _ in TRIAGE_DOMAINS}
    st.session_state.rubric_total = 0
    st.session_state.strobe_checks = {}
    st.session_state.design = "Cohort"
    st.session_state.title = ""
    st.session_state.question = ""
    st.session_state.index = ""
    st.session_state.period = ""
    st.session_state.sites = ""
    st.session_state.irb = ""
    st.session_state.upgrades = []
    st.session_state.gates_pass = False
    st.session_state.gate_b_items = GATE_B_MIN["Cohort"]

init_state()

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.title("🧭 Triage + STROBE")
    st.markdown("Use this tool to **triage** TriNetX study ideas and ensure **STROBE**-aligned reporting for observational designs.")
    st.divider()
    st.subheader("Design")
    design = st.selectbox("Select study design", ["Cohort", "Case–control", "Cross-sectional"], index=["Cohort","Case–control","Cross-sectional"].index(st.session_state.design))
    if design != st.session_state.design:
        st.session_state.design = design
        st.session_state.gate_b_items = GATE_B_MIN.get(design, [])
        # Reset STROBE checks for new design
        st.session_state.strobe_checks = {}

    st.caption("Note: For quasi-experimental designs (DiD/ITS), use this as a baseline STROBE checklist and add design-specific reporting (parallel trends, event study, autocorrelation, robust SEs).")

    st.divider()
    st.subheader("Save/Load")
    col_save, col_load = st.columns(2)
    with col_save:
        if st.button("💾 Download JSON state"):
            payload = json.dumps({k: v for k, v in st.session_state.items() if k != "initialized"}, indent=2)
            st.download_button("Save current state", payload, file_name="triage_strobe_state.json")
    with col_load:
        uploaded = st.file_uploader("Load saved JSON", type=["json"], accept_multiple_files=False, label_visibility="collapsed")
        if uploaded:
            data = json.load(uploaded)
            for k, v in data.items():
                st.session_state[k] = v
            st.success("State loaded.")

# ----------------------------
# Main Layout
# ----------------------------

st.title("TriNetX Study Triage + STROBE Planner")
st.write("Raise the analytic bar and route projects to **Manuscript / Brief / Abstract / Poster** with transparent criteria and STROBE-aligned reporting.")

# Project Basics
st.header("1) Project Basics")
c1, c2, c3 = st.columns([1.2,1,1])
with c1:
    st.session_state.title = st.text_input("Study title", value=st.session_state.title)
    st.session_state.question = st.text_area("Clinical question (PECO/PECOS)", value=st.session_state.question, height=100, help="Population, Exposure/Comparator, Outcome(s), Setting/Time-window.")
with c2:
    st.session_state.index = st.text_input("Index date definition", value=st.session_state.index, help="e.g., first prescription date; diagnosis date with washout; etc.")
    st.session_state.period = st.text_input("Data period", value=st.session_state.period, help="e.g., 2010–2024; pre/post ICD-10; pandemic era considered.")
with c3:
    st.session_state.sites = st.text_input("Sites / HCOs", value=st.session_state.sites, help="List included networks/sites or note if multi-network TriNetX.")
    st.session_state.irb = st.text_input("IRB / Privacy", value=st.session_state.irb, help="e.g., IRB exemption, data use agreements, privacy notes.")

st.divider()

# Gate A
st.header("2) Gate A — Fatal Flaw Screen")
gate_cols = st.columns(2)
gate_a_flags = []
for i, (key, label) in enumerate(GATE_A_ITEMS):
    with gate_cols[i % 2]:
        st.session_state.gate_a[key] = st.checkbox(label, value=st.session_state.gate_a[key])
        gate_a_flags.append(st.session_state.gate_a[key])

gates_pass = all(gate_a_flags)
st.session_state.gates_pass = gates_pass
st.info("All Gate A items must be checked to proceed to **Manuscript/Brief** tracks.", icon="ℹ️") if gates_pass else st.warning("One or more Gate A items are unchecked. Consider **refactor/downgrade** until resolved.", icon="⚠️")

st.divider()

# Gate B
st.header(f"3) Gate B — Minimum Standards ({st.session_state.design})")
st.session_state.gate_b = {}
for item in st.session_state.gate_b_items:
    st.session_state.gate_b[item] = st.checkbox(item, value=st.session_state.gate_b.get(item, False), key=f"gateb_{item}")

st.divider()

# STROBE Checklist
st.header("4) STROBE Checklist (reporting)")
st.caption("Mark each item as addressed and note where/how it will appear in the manuscript (section/figure/table).")
strobe_items = strobe_items_for_design(st.session_state.design)

if not st.session_state.strobe_checks:
    st.session_state.strobe_checks = {k: {"section": sec, "prompt": prompt, "addressed": False, "where": ""} for k, sec, prompt in strobe_items}

# Render checklist
strobe_df_rows = []
for key, sec, prompt in strobe_items:
    row = st.session_state.strobe_checks.get(key, {"section": sec, "prompt": prompt, "addressed": False, "where": ""})
    with st.expander(f"{key} • {sec}: {prompt}", expanded=False):
        addr = st.checkbox("Addressed", value=row["addressed"], key=f"strobe_{key}")
        where = st.text_input("Where/How (section/figure/table)", value=row.get("where",""), key=f"strobe_where_{key}")
    row["addressed"] = st.session_state[f"strobe_{key}"]
    row["where"] = st.session_state[f"strobe_where_{key}"]
    row["section"] = sec
    row["prompt"] = prompt
    st.session_state.strobe_checks[key] = row
    strobe_df_rows.append({"Item": key, "Section": sec, "Prompt": prompt, "Addressed": row["addressed"], "Where/How": row["where"]})

strobe_yes, strobe_total, strobe_pct = compute_strobe_score(st.session_state.strobe_checks)
st.progress(strobe_pct/100.0, text=f"STROBE completeness: {strobe_yes}/{strobe_total} ({strobe_pct:.1f}%)")

st.divider()

# Rubric
st.header("5) Scored Triage Rubric (0–2 each; max 24)")
rubric_cols = st.columns(3)
total_score = 0
for i, (dom, desc) in enumerate(TRIAGE_DOMAINS):
    with rubric_cols[i % 3]:
        score = st.radio(
            dom,
            options=[0,1,2],
            index=[0,1,2].index(st.session_state.rubric.get(dom, 0)),
            horizontal=True,
            help=desc,
            key=f"rubric_{dom}"
        )
        st.session_state.rubric[dom] = score
        total_score += score
st.session_state.rubric_total = total_score
st.metric("Rubric Total", f"{total_score} / 24")

st.divider()

# Depth Upgrades
st.header("6) Depth-Upgrade Menu")
sel = []
upgrade_cols = st.columns(2)
for i, u in enumerate(DEPTH_UPGRADES):
    with upgrade_cols[i % 2]:
        checked = st.checkbox(u, value=(u in st.session_state.get("upgrades", [])), key=f"up_{i}")
        if checked:
            sel.append(u)
st.session_state.upgrades = sel

st.divider()

# Decision
st.header("7) Decision & Rationale")
dec, why = triage_decision(st.session_state.rubric_total, strobe_pct, st.session_state.gates_pass and all(st.session_state.gate_b.values()) if st.session_state.gate_b else st.session_state.gates_pass)
cA, cB, cC = st.columns([1.3,1,1])
with cA:
    st.subheader(f"Recommended Track: {dec}")
    st.write(why)
with cB:
    st.metric("STROBE %", f"{strobe_pct:.1f}%")
with cC:
    st.metric("Rubric", f"{st.session_state.rubric_total}/24")

# Optional flowchart (Graphviz)
try:
    import graphviz
    dot = graphviz.Digraph()
    dot.attr(rankdir="LR")
    dot.node("A", "Idea + Clinical Question")
    dot.node("B", "Gate A: Fatal Flaws?")
    dot.node("C", f"Gate B: Minimums ({st.session_state.design})")
    dot.node("D", "Score 12-item Rubric")
    dot.node("E", "Decision")
    dot.edges([("A","B"), ("B","C"), ("C","D"), ("D","E")])
    st.subheader("Flow")
    st.graphviz_chart(dot)
except Exception:
    pass

st.divider()

# Export
st.header("8) Export Report")
if st.button("Generate Markdown Report"):
    state = {
        "title": st.session_state.title,
        "question": st.session_state.question,
        "design": st.session_state.design,
        "index": st.session_state.index,
        "period": st.session_state.period,
        "sites": st.session_state.sites,
        "irb": st.session_state.irb,
        "gate_a": st.session_state.gate_a,
        "gate_b": st.session_state.gate_b,
        "gate_b_items": st.session_state.gate_b_items,
        "strobe_checks": st.session_state.strobe_checks,
        "rubric": st.session_state.rubric,
        "rubric_total": st.session_state.rubric_total,
        "upgrades": st.session_state.upgrades,
        "gates_pass": st.session_state.gates_pass,
    }
    md = make_report_md(state)
    st.download_button("⬇️ Download triage_report.md", md, file_name="triage_strobe_report.md")
''')

reqs = "streamlit\npandas\n"

md = make_report_md(state)
st.download_button("⬇️ Download triage_report.md", md, file_name="triage_strobe_report.md")

"/mnt/data/triage_strobe_app.py written, and /mnt/data/requirements.txt created."

