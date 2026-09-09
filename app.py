from __future__ import annotations

import calendar
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PUK CoW Assurance", page_icon="✅", layout="wide")

# -----------------------------
# Configuration from supplied KPI specification
# -----------------------------
SITE_TARGETS_KPI1 = {
    "Dimlington": {"routine": 1, "non_routine": 1},
    "Cleeton": {"routine": 1, "non_routine": 1},
    "Ravenspurn North": {"routine": 1, "non_routine": 1},
    "Northern NUI's": {"routine": 2, "non_routine": 1},
    "Bacton": {"routine": 1, "non_routine": 1},
    "Leman 27BC": {"routine": 1, "non_routine": 1},
    "Southern NUI's": {"routine": 2, "non_routine": 1},
}

KPI2_SITES = [
    "Ravenspurn North", "Cleeton", "Northern Flying Team", "Northern W2W",
    "Dimlington", "Leman 27BC", "Southern Flying Team", "Southern W2W", "Bacton"
]

KPI4_WEEKLY_ROLES = {"W2W OOE": 1, "Medic HSEA": 1}
KPI4_QUARTERLY_ROLES = {"Field Hub OIM": 1}

# BAR remains visible in the prototype but is not auto-assigned because the three supplied source forms
# do not contain question-level BAR classifications. Users can classify findings manually until an approved
# BAR mapping is supplied.
BAR_OPTIONS = ["Unclassified", "BAR 1", "BAR 2", "BAR 3"]

PERMIT_QUALITY_QUESTIONS = [
    ("Planning", "Is the activity planned to be undertaken outside the next 24 hours?"),
    ("Planning", "Has the WCC been discussed in the daily permit meeting?"),
    ("Planning", "Have current ORA's been considered and their impact on the activity/task understood?"),
    ("Planning", "Has a worksite visit been undertaken by the PA and AA to identify task hazards?"),
    ("Raising a NEW WCC", "Is there a brief, clear and concise scope summary and task duration identified?"),
    ("Raising a NEW WCC", "Is the work location, tools and equipment described clearly and specifically?"),
    ("Raising a NEW WCC", "Has increased error risk from similar/adjacent equipment, labelling or unfamiliarity been considered and controlled?"),
    ("Raising a NEW WCC", "Is the method for undertaking the task clear?"),
    ("Raising a NEW WCC", "Is the WCC specific to the task and not generic?"),
    ("Raising a NEW WCC", "Is the work party competent and authorised, with evidence of relevant PCAP, task-specific and higher-risk competency requirements where applicable?"),
    ("Issuing a Routine WCC", "Is the Routine WCC used for individual, low-risk and regularly performed activities?"),
    ("Issuing a Routine WCC", "Is the routine task description suitable and sufficiently specific?"),
    ("Issuing a Routine WCC", "Where breaking containment is involved, has thorough hazard identification been completed?"),
    ("Identifying the Correct WCC", "Has the correct WCC type and risk assessment level been selected for the task?"),
    ("Identifying the Correct WCC", "Where supplementary risk evaluation is required (e.g. BOC, COSHH, HAVS, manual handling), has it been completed?"),
    ("Level 2 Risk Assessment", "Has a suitable three-person risk-assessment team participated and is the task risk-assessment team leader competent?"),
    ("Risk Assessment - Task Steps", "Is the task broken into clearly defined steps in the sequence it will be done?"),
    ("Clear Hazard Identification Statements", "Is it clear what the hazard is and who/what might be harmed, with one hazard per statement?"),
    ("Clear Control Statements", "Are control statements clear on who is doing what and when, using simple and concise language?"),
    ("Control Effectiveness", "Is the risk reduction credible and has the risk of error from numerous assigned actions been considered?"),
    ("Hierarchy of Controls", "Does the assessment favour higher-order controls such as elimination/substitution over procedures/PPE where reasonably practicable?"),
    ("Low Value Hazards & Controls", "Is the WCC free from low-value hazards/controls that do not actively reduce risk or simply repeat standard measures?"),
    ("Low Value Hazards & Controls", "Are controls verifiable and specific rather than vague terms such as decide/consider/if required?"),
    ("Isolation Requirements", "Have all ICC controls been acknowledged and transferred to the WCC?"),
    ("Low Risk Tasks", "Is the site actively monitored to ensure work is not undertaken without an appropriate WCC?"),
    ("Low Risk Tasks", "For non-permit tasks, is a toolbox talk completed?"),
]

LEADERSHIP_QUESTIONS = [
    ("Permit to Work", "Are personnel able to explain the work they are undertaking?"),
    ("Permit to Work", "Have personnel reviewed and understood the permit requirements?"),
    ("Permit to Work", "Is the permit available at the worksite and applicable to the work being undertaken?"),
    ("Permit to Work", "Are routine permits being used for low-risk tasks and are they not generic?"),
    ("Permit to Work", "Do personnel understand when work should stop and the permit be revalidated?"),
    ("Hazard Identification & Risk Assessment", "Can personnel explain the key hazards associated with the task?"),
    ("Hazard Identification & Risk Assessment", "Can personnel describe the controls used to manage the hazards?"),
    ("Hazard Identification & Risk Assessment", "Have any conditions changed since work commenced?"),
    ("Hazard Identification & Risk Assessment", "Have Major Accident Hazard risks been considered where applicable?"),
    ("Hazard Identification & Risk Assessment", "Are environmental hazards and controls understood?"),
    ("Toolbox Talks & Workforce Understanding", "Have personnel participated in the Toolbox Talk for the task?"),
    ("Toolbox Talks & Workforce Understanding", "Can personnel explain the key points discussed during the Toolbox Talk?"),
    ("Toolbox Talks & Workforce Understanding", "Have personnel had the opportunity to ask questions or raise concerns?"),
    ("Worksite Compliance", "Are permit controls being implemented at the worksite?"),
    ("Worksite Compliance", "Are barriers, isolations, PPE and other controls in place and maintained?"),
    ("Worksite Compliance", "Is the work being carried out as described within the permit?"),
    ("Worksite Compliance", "Are there any examples of conditions differing from those described in the permit?"),
    ("Supervision & Leadership", "Is supervision visible and appropriate for the task risk?"),
    ("Supervision & Leadership", "Have supervisors recently visited the worksite?"),
    ("Supervision & Leadership", "Are concerns raised by personnel being addressed effectively?"),
    ("Supervision & Leadership", "Do personnel feel adequately supported by site leadership?"),
    ("Stop the Job Culture", "Do personnel understand their authority to stop the job?"),
    ("Stop the Job Culture", "Would personnel feel comfortable challenging unsafe conditions?"),
    ("Stop the Job Culture", "Can personnel explain what circumstances would trigger a Stop the Job intervention?"),
    ("Stop the Job Culture", "Are there any barriers preventing personnel from raising concerns?"),
    ("Learning & Continuous Improvement", "Are personnel aware of relevant recent incidents or safety alerts relating to CoW?"),
    ("Learning & Continuous Improvement", "Are gaps in permit quality/compliance identified through audits, recorded, actioned and tracked to completion?"),
]

TBT_QUESTIONS = [
    ("TBT Hazard Identification", "Does the TBT lead discuss the hazards and controls associated with the task/activity?"),
    ("TBT Hazard Identification", "Are SIMOP activities that may conflict with the task discussed?"),
    ("TBT Hazard Identification", "Are spills and proximity to open drains discussed and controls understood?"),
    ("TBT Hazard Identification", "Is situational awareness, including dropped-object potential, discussed and acted upon?"),
    ("TBT Hazard Identification", "Are isolations identified, checked and discussed?"),
    ("TBT Hazard Identification", "Are emergency response arrangements discussed and understood?"),
    ("TBT Hazard Identification", "If additional significant hazards are identified, is the job stopped and the TRA reassessed/re-authorised?"),
    ("TBT Hazard Identification", "Is the TBT used for its intended purpose: task detail, energy prompts, controls, supporting documents and minor additional hazards?"),
    ("TBT Understanding the Task", "Are open questions used to engage the work party?"),
    ("TBT Understanding the Task", "Is the activity broken down into significant steps?"),
    ("TBT Understanding the Task", "Is the method for each step clear?"),
    ("TBT Understanding the Task", "Has the work party actively participated and signed the TBT?"),
    ("TBT Understanding the Task", "For lone work, has the PA completed the TBT with the AA before commencing?"),
    ("Worksite & Equipment", "Are tools/equipment identified on the risk assessment with adequate controls?"),
    ("Worksite & Equipment", "Are hazards associated with transporting tools/equipment to the worksite controlled?"),
    ("Worksite & Equipment", "Are access and egress points checked and clear?"),
    ("Permit Compliance", "Is an up-to-date WCC at the worksite and signed by all work-party members?"),
    ("Permit Compliance", "Is the permit specific to the task and not generic?"),
    ("Permit Compliance", "Is the task broken into clearly defined steps in the correct sequence?"),
    ("Implementing Controls", "Where required, are gas tests completed/recorded and a detector available?"),
    ("Implementing Controls", "Have all permit controls been implemented?"),
    ("Implementing Controls", "Are supplementary controls (e.g. COSHH, manual handling, HAVS, BOC) implemented and understood?"),
    ("Implementing Controls", "Where substances are used, does the work party understand emergency actions?"),
    ("Implementing Controls", "Have additional method statements been reviewed, recorded and complied with?"),
    ("Permit Authorisation", "Has the permit undergone the correct level of authorisation?"),
    ("Permit Authorisation", "For NUI work, have all Level 2 RA activities been discussed with the hub OIM before authorisation/issue?"),
    ("Managing Low Risk Activities", "Is the routine WCC suitable and specific enough to justify low risk?"),
    ("Managing Low Risk Activities", "For tasks that do not require a permit, has a TBT been completed?"),
]

POP_QUESTIONS = [
    ("Process Operating Procedures", "Has a TBT been completed before work commences?"),
    ("Process Operating Procedures", "Is the POP being followed in the correct sequence, including valve line-up where appropriate?"),
    ("Process Operating Procedures", "Are two-person signatures applied for critical steps?"),
    ("Process Operating Procedures", "Are operators using the most up-to-date POP and are controlled documents managed effectively?"),
    ("Process Operating Procedures", "Is the POP within review date and transferred to the new format/task screening assessment where required?"),
    ("Process Operating Procedures", "Are completed POPs scanned and uploaded to the designated storage area?"),
    ("Process Operating Procedures", "Is the handover section signed and countersigned by outgoing/incoming OTLs?"),
]


def month_weeks(year: int, month: int) -> int:
    # Count calendar Mondays as a pragmatic proxy for weekly minimum planning.
    cal = calendar.monthcalendar(year, month)
    return sum(1 for wk in cal if wk[calendar.MONDAY] != 0)


def quarter_of(d: pd.Timestamp) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def status_standard(completion: float, conformance: float) -> str:
    if completion >= 100 and conformance >= 90:
        return "Green"
    if completion < 70 or conformance < 70:
        return "Red"
    return "Amber"


def status_kpi3(visits: int, conformance: float, coverage_ok: bool) -> str:
    if visits >= 3 and conformance >= 90 and coverage_ok:
        return "Green"
    if visits <= 1 or conformance < 70:
        return "Red"
    return "Amber"


def status_kpi5(trend_delta: int, hipo: int, significant: int, loc: int, repeat_theme: bool) -> str:
    if trend_delta > 2 or hipo > 1 or significant > 1 or loc > 1 or repeat_theme:
        return "Red"
    if trend_delta > 0 or hipo == 1 or significant == 1 or loc == 1:
        return "Amber"
    return "Green"


def status_badge(status: str) -> str:
    icon = {"Green": "🟢", "Amber": "🟠", "Red": "🔴"}.get(status, "⚪")
    return f"{icon} {status}"


def make_mock_data(seed: int = 7):
    import random
    random.seed(seed)
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=180))
    audits = []
    actions = []
    sites = list(SITE_TARGETS_KPI1)
    auditors = ["A. Smith", "J. Brown", "R. Taylor", "S. Jones"]
    roles = ["Site Controller", "Asset Superintendent", "W2W OOE", "Medic HSEA", "Field Hub OIM", "Operations Director"]
    audit_types = ["Permit Quality", "TBT / Permit Compliance", "Leadership Engagement"]
    for i in range(150):
        d = start + timedelta(days=random.randint(0, 180))
        typ = random.choices(audit_types, weights=[55, 30, 15])[0]
        site = random.choice(sites)
        role = random.choice(roles)
        n_q = random.choice([12, 16, 20, 26])
        no = random.choices(range(0, 6), weights=[40, 25, 15, 10, 6, 4])[0]
        na = random.randint(0, 2)
        yes = max(n_q - no - na, 0)
        applicable = yes + no
        conf = 100 * yes / applicable if applicable else 100
        overall = "Meets" if no == 0 else "Does not meet"
        routine = random.random() < 0.45
        audits.append({
            "audit_id": f"A-{i+1:04d}", "date": pd.Timestamp(d), "audit_type": typ,
            "site": site, "team": random.choice(["W2W North", "W2W South", "Flying North", "Flying South", "Core"]),
            "auditor": random.choice(auditors), "auditor_role": role,
            "permit_type": "Routine" if routine else "Non-routine", "yes": yes, "no": no, "na": na,
            "conformance_pct": round(conf, 1), "overall": overall,
            "positive_practice": random.choice(["", "Good PA engagement", "Clear isolation controls", "Strong TBT participation"]),
            "wai_wad_gap": random.choice(["None", "Control present in permit but weak at worksite", "Worksite control stronger than documented", "Minor documentation mismatch"]),
        })
        for j in range(no):
            actions.append({
                "action_id": f"ACT-{len(actions)+1:04d}", "audit_id": f"A-{i+1:04d}", "date": pd.Timestamp(d),
                "site": site, "audit_type": typ,
                "bar": random.choice(BAR_OPTIONS),
                "finding": random.choice(["Permit not task specific", "Control wording not verifiable", "TBT hazard discussion incomplete", "Worksite control not fully implemented", "Leadership coverage gap"]),
                "action": random.choice(["Review WCC and reissue", "Coach permit issuer", "Update task risk assessment", "Verify control at worksite", "Schedule targeted leadership visit"]),
                "owner": random.choice(["Site Controller", "Asset Superintendent", "HSEA", "AA"]),
                "due_date": pd.Timestamp(d + timedelta(days=random.choice([7, 14, 30]))),
                "status": random.choice(["Open", "Open", "Closed"]),
            })
    audits_df = pd.DataFrame(audits)
    actions_df = pd.DataFrame(actions)

    # Mock MOI series: one row per month, synthetic only.
    moi = []
    for m in pd.date_range(start=pd.Timestamp(start).to_period('M').start_time, periods=7, freq='MS'):
        moi.append({"month": m, "permit_incidents": random.choice([0, 1, 1, 2, 2, 3]),
                    "hipo": random.choice([0, 0, 0, 1]), "significant_injury": random.choice([0, 0, 0, 1]),
                    "loss_of_containment": random.choice([0, 0, 1]), "repeat_theme": random.choice([False, False, False, True])})
    return audits_df, actions_df, pd.DataFrame(moi)


if "audits" not in st.session_state:
    st.session_state.audits, st.session_state.actions, st.session_state.moi = make_mock_data()


def append_audit_record(record: dict, response_rows: List[dict]):
    df = pd.DataFrame([record])
    st.session_state.audits = pd.concat([st.session_state.audits, df], ignore_index=True)
    for rr in response_rows:
        if rr["response"] == "No":
            st.session_state.actions = pd.concat([
                st.session_state.actions,
                pd.DataFrame([{
                    "action_id": f"ACT-{len(st.session_state.actions)+1:04d}",
                    "audit_id": record["audit_id"], "date": record["date"], "site": record["site"],
                    "audit_type": record["audit_type"], "bar": rr.get("bar", "Unclassified"),
                    "finding": rr["question"], "action": rr.get("smart_action", ""),
                    "owner": rr.get("owner", ""), "due_date": rr.get("due_date", pd.NaT), "status": "Open"
                }])
            ], ignore_index=True)


def render_audit_form(title: str, audit_type: str, questions: List[tuple], allow_pop=False, leadership=False):
    st.subheader(title)
    with st.form(f"form_{audit_type}", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        audit_date = c1.date_input("Audit date", value=date.today())
        site = c2.selectbox("Site / installation", list(SITE_TARGETS_KPI1.keys()) + ["Other"])
        team = c3.text_input("Team")
        c1, c2, c3 = st.columns(3)
        auditor = c1.text_input("Auditor / leadership representative")
        auditor_role = c2.selectbox("Role", ["Site Controller", "Asset Superintendent", "W2W OOE", "Medic HSEA", "Field Hub OIM", "Operations Director", "Other"])
        site_controller = c3.text_input("Site Controller")
        c1, c2, c3 = st.columns(3)
        permit_type = c1.selectbox("Activity / permit type", ["Routine", "Non-routine", "POP"] if allow_pop else ["Routine", "Non-routine"])
        ref = c2.text_input("WCC / POP number")
        description = c3.text_input("Description")
        if leadership:
            st.caption("Source rule: one 'No' means the Leadership Engagement Checklist does not meet the CoW standard. N/A should be noted where appropriate.")
        if allow_pop and permit_type == "POP":
            shown_questions = questions[:13] + POP_QUESTIONS  # TBT + POP branch
        else:
            shown_questions = questions

        responses = []
        current_section = None
        for idx, (section, q) in enumerate(shown_questions, 1):
            if section != current_section:
                st.markdown(f"### {section}")
                current_section = section
            cols = st.columns([4.8, 1.2, 1.2])
            cols[0].markdown(f"**{idx}. {q}**")
            response = cols[1].selectbox("Response", ["Yes", "No", "N/A"], key=f"{audit_type}_{idx}_resp", label_visibility="collapsed")
            bar = cols[2].selectbox("BAR", BAR_OPTIONS, key=f"{audit_type}_{idx}_bar", label_visibility="collapsed")
            evidence = st.text_input("Comments / evidence", key=f"{audit_type}_{idx}_ev", placeholder="Comments / evidence")
            smart_action = ""
            owner = ""
            due_date = pd.NaT
            if response == "No":
                a1, a2, a3 = st.columns([3, 1.4, 1.2])
                smart_action = a1.text_input("SMART action", key=f"{audit_type}_{idx}_act", placeholder="Required corrective action")
                owner = a2.text_input("Action owner", key=f"{audit_type}_{idx}_owner")
                due_date = a3.date_input("Due", value=date.today()+timedelta(days=30), key=f"{audit_type}_{idx}_due")
            responses.append({"section": section, "question": q, "response": response, "bar": bar,
                              "evidence": evidence, "smart_action": smart_action, "owner": owner, "due_date": pd.Timestamp(due_date) if pd.notna(due_date) else pd.NaT})

        positive = st.text_area("Positive observations / good practice")
        wad = st.text_area("Work as Done observation / difference from documented controls", placeholder="Record any meaningful gap between documented controls and actual work execution")
        submitted = st.form_submit_button("Save audit", use_container_width=True)

    if submitted:
        yes = sum(r["response"] == "Yes" for r in responses)
        no = sum(r["response"] == "No" for r in responses)
        na = sum(r["response"] == "N/A" for r in responses)
        applicable = yes + no
        conf = 100 * yes / applicable if applicable else 100
        overall = "Meets" if no == 0 else "Does not meet"
        audit_id = f"A-{len(st.session_state.audits)+1:04d}"
        record = {
            "audit_id": audit_id, "date": pd.Timestamp(audit_date), "audit_type": audit_type,
            "site": site, "team": team, "auditor": auditor, "auditor_role": auditor_role,
            "permit_type": permit_type, "yes": yes, "no": no, "na": na,
            "conformance_pct": round(conf, 1), "overall": overall,
            "positive_practice": positive, "wai_wad_gap": wad or "None",
        }
        append_audit_record(record, responses)
        st.success(f"Saved {audit_id}: {overall} CoW standard, {conf:.1f}% question conformance, {no} non-conformance(s).")


# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.title("PUK CoW Assurance")
st.sidebar.caption("Streamlit prototype • synthetic test data")
all_audits = st.session_state.audits.copy()
all_audits["date"] = pd.to_datetime(all_audits["date"])
min_d = all_audits["date"].min().date()
max_d = max(date.today(), all_audits["date"].max().date())
range_sel = st.sidebar.date_input("Reporting period", value=(max(min_d, max_d-timedelta(days=90)), max_d))
if isinstance(range_sel, tuple) and len(range_sel) == 2:
    start_d, end_d = range_sel
else:
    start_d, end_d = min_d, max_d
site_filter = st.sidebar.multiselect("Site", sorted(all_audits["site"].dropna().unique()), default=[])
auditor_filter = st.sidebar.multiselect("Auditor", sorted(all_audits["auditor"].dropna().unique()), default=[])
permit_filter = st.sidebar.multiselect("Permit type", sorted(all_audits["permit_type"].dropna().unique()), default=[])

filtered = all_audits[(all_audits["date"].dt.date >= start_d) & (all_audits["date"].dt.date <= end_d)].copy()
if site_filter:
    filtered = filtered[filtered["site"].isin(site_filter)]
if auditor_filter:
    filtered = filtered[filtered["auditor"].isin(auditor_filter)]
if permit_filter:
    filtered = filtered[filtered["permit_type"].isin(permit_filter)]

st.title("Control of Work Assurance")
st.caption("KPI-led prototype based on the supplied July 2026 CoW KPI specification and three assurance checklists. Test data is synthetic.")

main_tabs = st.tabs(["Dashboard", "Complete Assurance", "Findings & Actions", "Analysis", "Data / Export"])

with main_tabs[0]:
    if filtered.empty:
        st.warning("No data for the current filters.")
    else:
        year = end_d.year
        month = end_d.month
        weeks = month_weeks(year, month)
        current_month = filtered[(filtered["date"].dt.year == year) & (filtered["date"].dt.month == month)]

        # KPI 1: Site Controller Permit Quality
        k1 = current_month[(current_month["audit_type"] == "Permit Quality") & (current_month["auditor_role"] == "Site Controller")]
        expected1 = 0
        if site_filter:
            target_sites = [s for s in site_filter if s in SITE_TARGETS_KPI1]
        else:
            target_sites = list(SITE_TARGETS_KPI1)
        for s in target_sites:
            t = SITE_TARGETS_KPI1[s]
            expected1 += (t["routine"] + t["non_routine"]) * weeks
        completion1 = 100 * len(k1) / expected1 if expected1 else 0
        conf1 = k1["conformance_pct"].mean() if len(k1) else 0
        status1 = status_standard(completion1, conf1)

        # KPI 2: Asset Superintendent Permit Quality - 1/week minimum across rotational assets
        k2 = current_month[(current_month["audit_type"] == "Permit Quality") & (current_month["auditor_role"] == "Asset Superintendent")]
        expected2 = weeks
        completion2 = 100 * len(k2) / expected2 if expected2 else 0
        conf2 = k2["conformance_pct"].mean() if len(k2) else 0
        status2 = status_standard(completion2, conf2)

        # KPI 3: leadership engagement - quarter
        end_ts = pd.Timestamp(end_d)
        q = quarter_of(end_ts)
        qdf = filtered[filtered["date"].apply(quarter_of) == q]
        k3 = qdf[qdf["audit_type"] == "Leadership Engagement"]
        visits3 = len(k3)
        conf3 = k3["conformance_pct"].mean() if len(k3) else 0
        coverage3 = k3["team"].nunique() >= min(3, visits3) if visits3 else False
        status3 = status_kpi3(visits3, conf3, coverage3)

        # KPI 4: site leadership TBT/Permit compliance. Prototype completion = aggregate weekly role achievement.
        k4 = current_month[current_month["audit_type"] == "TBT / Permit Compliance"]
        expected4 = 0
        for role, n in KPI4_WEEKLY_ROLES.items():
            expected4 += n * weeks
        # Field Hub OIM is quarterly, only count target in last month of quarter to avoid overstating monthly requirement.
        if month in (3, 6, 9, 12):
            expected4 += 1
        completion4 = 100 * len(k4[k4["auditor_role"].isin(list(KPI4_WEEKLY_ROLES)+list(KPI4_QUARTERLY_ROLES))]) / expected4 if expected4 else 0
        conf4 = k4["conformance_pct"].mean() if len(k4) else 0
        status4 = status_standard(completion4, conf4)

        # KPI5 synthetic MOI
        moi = st.session_state.moi.sort_values("month")
        latest = moi.iloc[-1]
        previous_12 = moi.iloc[:-1]["permit_incidents"].sum()
        # Prototype trend: latest three-month average vs prior three-month average proxy when <12 months demo data.
        recent = moi.tail(3)["permit_incidents"].sum()
        prior = moi.iloc[max(0, len(moi)-6):max(0, len(moi)-3)]["permit_incidents"].sum()
        delta5 = int(recent - prior)
        status5 = status_kpi5(delta5, int(latest.hipo), int(latest.significant_injury), int(latest.loss_of_containment), bool(latest.repeat_theme))

        cards = [
            ("KPI 1 • Tier 3", "Site Controller Permit Quality", status1, f"{completion1:.0f}% plan", f"{conf1:.0f}% conformance"),
            ("KPI 2 • Tier 2", "Asset Superintendent Permit Quality", status2, f"{completion2:.0f}% plan", f"{conf2:.0f}% conformance"),
            ("KPI 3 • Tier 2", "Leadership NUI Engagement", status3, f"{visits3}/3 quarterly visits", f"{conf3:.0f}% conformance"),
            ("KPI 4 • Tier 3", "Site Leadership Visits / TBT", status4, f"{completion4:.0f}% plan", f"{conf4:.0f}% conformance"),
            ("KPI 5 • Tier 1", "Permit-controlled Incidents", status5, f"Trend Δ {delta5:+d}", "Rolling trend input"),
        ]
        cols = st.columns(5)
        for c, (tier, title, stat, v1, v2) in zip(cols, cards):
            with c:
                st.markdown(f"**{tier}**")
                st.metric(title, status_badge(stat), help=f"{v1} • {v2}")
                st.caption(f"{v1}  |  {v2}")

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Audits in period", len(filtered))
        c2.metric("Overall conformance", f"{filtered['conformance_pct'].mean():.1f}%")
        c3.metric("Audits not meeting CoW standard", int((filtered["overall"] == "Does not meet").sum()))
        act = st.session_state.actions.copy()
        c4.metric("Open actions", int((act["status"] == "Open").sum()))

        st.subheader("Leadership view")
        l1, l2 = st.columns([1.5, 1])
        with l1:
            monthly = filtered.assign(month=filtered["date"].dt.to_period("M").astype(str)).groupby("month", as_index=False)["conformance_pct"].mean()
            st.line_chart(monthly.set_index("month"), height=260)
        with l2:
            by_type = filtered.groupby("audit_type")["conformance_pct"].mean().sort_values()
            st.bar_chart(by_type, height=260)

        st.subheader("Leadership narrative")
        red = [x[1] for x in cards if x[2] == "Red"]
        amber = [x[1] for x in cards if x[2] == "Amber"]
        strongest = filtered.groupby("site")["conformance_pct"].mean().sort_values(ascending=False)
        weakest = strongest.sort_values()
        narrative = []
        if red:
            narrative.append("Immediate attention is required for " + ", ".join(red) + ".")
        if amber:
            narrative.append("Intervention/review is indicated for " + ", ".join(amber) + ".")
        if not red and not amber:
            narrative.append("All five dashboard indicators are currently within the prototype Green criteria.")
        if len(strongest):
            narrative.append(f"Highest average assurance conformance in the selected period is {strongest.index[0]} ({strongest.iloc[0]:.1f}%), while {weakest.index[0]} is lowest ({weakest.iloc[0]:.1f}%).")
        gaps = filtered[filtered["wai_wad_gap"].fillna("None") != "None"]
        if len(gaps):
            common_gap = gaps["wai_wad_gap"].value_counts().idxmax()
            narrative.append(f"The most frequent Work as Imagined / Work as Done observation is: {common_gap}.")
        st.info(" ".join(narrative))

with main_tabs[1]:
    f_tabs = st.tabs(["Permit Quality", "Leadership Engagement", "TBT / Permit / POP"])
    with f_tabs[0]:
        render_audit_form("Level 4 Monitoring • Permit Quality", "Permit Quality", PERMIT_QUALITY_QUESTIONS)
    with f_tabs[1]:
        render_audit_form("Control of Work • Leadership Engagement", "Leadership Engagement", LEADERSHIP_QUESTIONS, leadership=True)
    with f_tabs[2]:
        render_audit_form("Level 4 Monitoring • Toolbox Talk, Permit Compliance & POP", "TBT / Permit Compliance", TBT_QUESTIONS, allow_pop=True)

with main_tabs[2]:
    st.subheader("Findings & actions")
    actions = st.session_state.actions.copy()
    if actions.empty:
        st.info("No findings/actions recorded.")
    else:
        af1, af2, af3 = st.columns(3)
        status_sel = af1.multiselect("Action status", sorted(actions["status"].dropna().unique()))
        bar_sel = af2.multiselect("BAR", BAR_OPTIONS)
        site_sel2 = af3.multiselect("Action site", sorted(actions["site"].dropna().unique()))
        view = actions.copy()
        if status_sel: view = view[view["status"].isin(status_sel)]
        if bar_sel: view = view[view["bar"].isin(bar_sel)]
        if site_sel2: view = view[view["site"].isin(site_sel2)]
        st.dataframe(view.sort_values(["status", "due_date"]), use_container_width=True, hide_index=True)
        st.caption("BAR is intentionally not auto-assigned in this build because the supplied source checklists do not include an approved question-level BAR mapping.")

with main_tabs[3]:
    st.subheader("Assurance analysis")
    if not filtered.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Conformance by site**")
            st.bar_chart(filtered.groupby("site")["conformance_pct"].mean().sort_values())
        with c2:
            st.markdown("**Conformance by auditor**")
            st.bar_chart(filtered.groupby("auditor")["conformance_pct"].mean().sort_values())

        st.markdown("**Routine vs non-routine permit quality**")
        pq = filtered[filtered["audit_type"] == "Permit Quality"]
        if len(pq):
            st.dataframe(pq.groupby("permit_type").agg(audits=("audit_id","count"), conformance=("conformance_pct","mean"), non_conforming=("overall", lambda x: (x=="Does not meet").sum())).round(1), use_container_width=True)

        st.markdown("**Work as Imagined vs Work as Done**")
        gaps = filtered[filtered["wai_wad_gap"].fillna("None") != "None"]
        if len(gaps):
            st.dataframe(gaps.groupby(["site", "wai_wad_gap"]).size().reset_index(name="observations").sort_values("observations", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No WAI/WAD differences recorded for the current filters.")

        st.markdown("**Repeat finding themes**")
        act = st.session_state.actions
        if len(act):
            st.dataframe(act.groupby(["finding", "bar"]).size().reset_index(name="count").sort_values("count", ascending=False).head(15), use_container_width=True, hide_index=True)

with main_tabs[4]:
    st.subheader("Data / export")
    st.write("Use this area to inspect the prototype datasets and export them for review.")
    d_tabs = st.tabs(["Audits", "Actions", "MOI"])
    with d_tabs[0]: st.dataframe(st.session_state.audits, use_container_width=True, hide_index=True)
    with d_tabs[1]: st.dataframe(st.session_state.actions, use_container_width=True, hide_index=True)
    with d_tabs[2]: st.dataframe(st.session_state.moi, use_container_width=True, hide_index=True)

    def csv_bytes(df):
        return df.to_csv(index=False).encode("utf-8")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download audits CSV", csv_bytes(st.session_state.audits), "cow_audits.csv", "text/csv", use_container_width=True)
    c2.download_button("Download actions CSV", csv_bytes(st.session_state.actions), "cow_actions.csv", "text/csv", use_container_width=True)
    c3.download_button("Download MOI CSV", csv_bytes(st.session_state.moi), "cow_moi.csv", "text/csv", use_container_width=True)

    st.markdown("### Prototype notes")
    st.write("• KPI 5 uses synthetic MOI data until a real MOI extract/schema is supplied.\n"
             "• BAR is available for manual classification but not auto-mapped to questions.\n"
             "• The monthly weekly-target calculation uses the number of Mondays in the month as a transparent planning proxy. This should be aligned to Perenco's final KPI reporting calendar before production.\n"
             "• Data currently persists only for the active Streamlit session. Production deployment should write to Snowflake / the approved corporate data layer.")
