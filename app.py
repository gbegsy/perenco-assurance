from __future__ import annotations

from datetime import date, timedelta
import json
import uuid

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PUK CoW Assurance Forms", page_icon="✅", layout="wide")

SITES = [
    "Dimlington", "Cleeton", "Ravenspurn North", "Northern NUI's", "Bacton",
    "Leman 27BC", "Southern NUI's", "Northern Flying Team", "Northern W2W",
    "Southern Flying Team", "Southern W2W", "Other"
]

RESPONSE_OPTIONS = ["", "Yes", "No", "N/A"]


# Questions flagged during Yes/No logic review. These are highlighted in red in the
# prototype because a simple Yes/No response can be reversed, conditional, compound,
# open-ended, or otherwise misleading for conformance scoring.
QUESTION_REVIEW_FLAGS = {
    # Permit Quality
    "Is the activity planned to be undertaken outside the next 24 hours?": (
        "Timing is not itself a compliance outcome; a legitimate task may be within 24 hours.",
        "Has the activity been planned within the required planning timescale and process?"
    ),
    "How is the team doing it? Is the method clear?": (
        "The first part is open-ended, so a Yes/No response does not fit cleanly.",
        "Is the method for completing the task clearly described and understood?"
    ),
    "Does the activity involve breaking of containment on ANY system? And has a thorough hazard identification been conducted to evaluate the associated risks?": (
        "This combines applicability with compliance. 'No breaking containment' could be acceptable but would score as No.",
        "Where breaking containment is involved, has a thorough hazard identification been completed and the associated risks adequately controlled? (Use N/A where breaking containment is not involved.)"
    ),
    "Has a team consisting of 3 persons (who have suitable knowledge of the task) taken part in the risk assessment? Is the task risk assessment team leader competent (check PCAP profile)?": (
        "Two separate compliance tests are combined; one could pass and the other fail.",
        "Split into two scored questions: (1) Has a suitably knowledgeable three-person team completed the assessment? (2) Is the assessment team leader competent for the role?"
    ),
    "Is it clear what the hazard is and who/what might be harmed? Is there only one hazard per statement?": (
        "Two separate checks are combined and could produce a mixed result.",
        "Split into two scored questions covering hazard/harm clarity and one-hazard-per-statement."
    ),
    "Are Control Statements clear on who is doing what and when? Is there enough detail to make it clear but short and concise? Is it clear and simple language?": (
        "Several separate quality criteria are combined into one Yes/No response.",
        "Split into clear responsibility/timing and clear/concise language checks."
    ),
    "Is the risk reduction credible? Have considerations been made to ensure that for those who have been given numerous actions, the risk of error is not increased?": (
        "Two different control-effectiveness tests are combined.",
        "Split credible risk reduction from action-loading/error-risk assessment."
    ),
    "Is the WCC free from hazards and controls which do not actively reduce the risk OR are part of standardised measures already in place, i.e. standards / Standard PPE etc.?": (
        "The negative construction and OR condition make Yes/No interpretation difficult.",
        "Does the WCC contain only task-relevant hazards and controls that actively reduce risk, excluding standard controls already covered elsewhere?"
    ),

    # Leadership Engagement
    "Have any conditions changed since work commenced?": (
        "A Yes may indicate a problem, while No may be satisfactory; this reverses normal scoring.",
        "Where conditions have changed since work commenced, has the work been stopped, reassessed and appropriately controlled before continuing? (Use N/A where conditions have not changed.)"
    ),
    "Have Major Accident Hazard (MAH) risks been considered where applicable?": (
        "'Where applicable' makes No ambiguous when no MAH exposure exists.",
        "Where applicable, have relevant Major Accident Hazard (MAH) risks been identified and appropriately controlled? (Use N/A where no relevant MAH exposure exists.)"
    ),
    "Are there any examples of conditions differing from those described in the permit?": (
        "A Yes indicates potential non-conformance, so the scoring direction is reversed.",
        "Do the actual worksite conditions match those described in the permit?"
    ),
    "Are there any barriers preventing personnel from raising concerns?": (
        "No is the desired outcome, but the current scoring treats No as a failure.",
        "Are personnel able to raise concerns or stop the work without barriers?"
    ),
    "Are sites identifying gaps in permit quality or compliance through audits? And are they recorded and actioned, tracked to completion?": (
        "This combines identification, recording, actioning and close-out in one response.",
        "Split into: (1) Are permit/compliance gaps being identified through audits? (2) Are identified gaps recorded, actioned and tracked to completion?"
    ),

    # TBT / Permit / POP
    "TBT Lead (typically the PA) discusses the hazards and controls associated to the task/activity (sourced from the Task Risk Assessment).": (
        "This is a statement rather than a clear Yes/No question.",
        "Has the TBT Lead discussed the task hazards and controls identified in the Task Risk Assessment with the work party?"
    ),
    "SIMOP activities that may conflict with the activity / task?": (
        "This is a prompt/fragment rather than a scored compliance question.",
        "Have relevant SIMOP activities that could conflict with the task been identified, discussed and controlled?"
    ),
    "Spills, and potential proximity to open drains discussed and how they can be avoided?": (
        "This is a fragment and does not clearly define the expected compliant outcome.",
        "Where relevant, have spill risks and proximity to open drains been discussed and appropriate controls agreed?"
    ),
    "Situation awareness, such as potential dropped objects (tools, equipment or structural) discussed and actions taken?": (
        "This is a fragment and combines discussion with action in one response.",
        "Have relevant situational hazards, including potential dropped objects, been discussed and appropriate controls implemented?"
    ),
    "Isolations, identified checked and discussed?": (
        "The wording is incomplete and could be interpreted inconsistently.",
        "Have all required isolations been identified, verified and discussed with the work party?"
    ),
    "Emergency response arrangements been discussed and everyone understands what to do?": (
        "The wording is incomplete and combines two checks.",
        "Have emergency response arrangements been discussed and can the work party explain what to do in an emergency?"
    ),
    "How is the team undertaking each step? Is the method clear?": (
        "The first part is open-ended, making the Yes/No response unclear.",
        "Is the method for undertaking each significant task step clear and understood by the work party?"
    ),
    "Where there is a Lone Work party, confirm that the PA has completed the TBT with the Area Authority (AA) prior to commencing the task.": (
        "This is an instruction and only applies to lone work, rather than a universal Yes/No question.",
        "For lone work, has the PA completed the TBT with the Area Authority before commencing the task? (Use N/A where the task is not lone work.)"
    ),
    "Are there any additional hazards transporting tools and equipment to the work site?": (
        "No may be the desired outcome, but current scoring treats No as a non-conformance.",
        "Have hazards associated with transporting tools and equipment to the worksite been identified and adequately controlled?"
    ),
}

PERMIT_SECTIONS = [
    ("1. Planning", [
        "Is the activity planned to be undertaken outside the next 24 hours?",
        "Has the WCC been discussed in the daily permit meeting?",
        "Have current ORA’s been considered, and how they may impact on the work activity or task?",
        "Has a work site visit been undertaken by the PA AND AA to identify the hazards associated to the task?",
    ]),
    ("2. Raising a NEW WCC: What is the task?", [
        "Is there a brief, clear and concise summary of scope? Has the duration of task been identified, i.e. one shift or several?",
        "Is the work location, tools and equipment described clearly and specific?",
        "Has the increased risk of error been considered and appropriate controls identified (e.g. physical verification by AA or attaching a work location label) where similar adjacent equipment is involved / non-standard equipment numbering / poorly labelled plant, or personnel unfamiliar with the worksite etc.?",
        "How is the team doing it? Is the method clear?",
        "Is the WCC SPECIFIC to the task and not generic?",
        "Is the work party competent and authorised to undertake the task, with evidence that relevant PCAP requirements, task-specific training, and additional competency requirements for higher-risk activities (e.g. Breaking Containment / Bolted joints)?",
    ]),
    ("3. Issuing a Routine WCC", [
        "Is the Routine WCC used for individual, low risk and regularly performed activities?",
        "Does the description of the task comply with question 2 and is it appropriate for the task?",
        "Does the activity involve breaking of containment on ANY system? And has a thorough hazard identification been conducted to evaluate the associated risks?",
    ]),
    ("4. Identifying the Correct WCC", [
        "Has the correct Type of WCC been selected appropriate for the task (Cold work, BOC etc.)? Has the correct risk assessment level been selected (Level 1 low risk / Level 2 higher risk) appropriate to the task?",
        "Where identified hazards require supplementary risk evaluation (BOC Checks, COSHH, HAVS, Manual handling, etc.), have these been completed?",
    ]),
    ("5. Level 2 Risk Assessment", [
        "Has a team consisting of 3 persons (who have suitable knowledge of the task) taken part in the risk assessment? Is the task risk assessment team leader competent (check PCAP profile)?",
    ]),
    ("6. Risk Assessment - Task Steps", [
        "Is the task broken down into clearly defined task steps on the WCC and does it detail the sequence in which it will be done?",
    ]),
    ("7. Clear Hazard Identification Statements", [
        "Is it clear what the hazard is and who/what might be harmed? Is there only one hazard per statement?",
    ]),
    ("8. Clear Control Statements", [
        "Are Control Statements clear on who is doing what and when? Is there enough detail to make it clear but short and concise? Is it clear and simple language?",
    ]),
    ("9. Control Effectiveness", [
        "Is the risk reduction credible? Have considerations been made to ensure that for those who have been given numerous actions, the risk of error is not increased?",
    ]),
    ("10. Hierarchy of Controls", [
        "Is the focus towards the higher level of control, i.e. ‘elimination’ and ‘substitution’ rather than the lower end of the hierarchy, i.e. procedures and PPE?",
    ]),
    ("11. Low Value Hazard & Controls (avoiding Clutter)", [
        "Is the WCC free from hazards and controls which do not actively reduce the risk OR are part of standardised measures already in place, i.e. standards / Standard PPE etc.?",
        "Are the controls capable of verifying and proving the risk gap has been closed and not vague using words such as ‘decide’ or ‘consider’ or ‘if required’?",
    ]),
    ("12. Isolation Requirements", [
        "Have all controls within the ICC been acknowledged and transferred to the WCC?",
    ]),
    ("13. Low Risk Tasks which do not require a WCC", [
        "Is the site actively monitored to ensure tasks are not being undertaken without an appropriate WCC?",
        "For those non-permit tasks, is a toolbox talk completed?",
    ]),
]

LEADERSHIP_SECTIONS = [
    ("Permit to Work (PTW)", [
        "Are personnel able to explain the work they are undertaking?",
        "Have personnel reviewed and understood the permit requirements?",
        "Is the permit available at the work site and applicable to the work being undertaken?",
        "Are routine permits being used for low-risk tasks and are not generic?",
        "Do personnel understand when work should stop and the permit revalidated?",
    ]),
    ("Hazard Identification & Risk Assessment", [
        "Can personnel explain the key hazards associated with the task?",
        "Can personnel describe the controls used to manage the hazards?",
        "Have any conditions changed since work commenced?",
        "Have Major Accident Hazard (MAH) risks been considered where applicable?",
        "Are environmental hazards and controls understood?",
    ]),
    ("Toolbox Talks & Workforce Understanding", [
        "Have personnel participated in the Toolbox Talk for the task?",
        "Can personnel explain the key points discussed during the Toolbox Talk?",
        "Have personnel had the opportunity to ask questions or raise concerns?",
    ]),
    ("Worksite Compliance", [
        "Are permit controls being implemented at the worksite?",
        "Are barriers, isolations, PPE and other controls in place and maintained?",
        "Is the work being carried out as described within the permit?",
        "Are there any examples of conditions differing from those described in the permit?",
    ]),
    ("Supervision & Leadership", [
        "Is supervision visible and appropriate for the task risk?",
        "Have supervisors recently visited the worksite?",
        "Are any concerns raised by personnel being addressed effectively?",
        "Do personnel feel adequately supported by site leadership?",
    ]),
    ("Stop the Job Culture", [
        "Do personnel understand their authority to stop the job?",
        "Would personnel feel comfortable challenging unsafe conditions?",
        "Can personnel explain what circumstances would trigger a Stop the Job intervention?",
        "Are there any barriers preventing personnel from raising concerns?",
    ]),
    ("Learning & Continuous Improvement", [
        "Are personnel aware of relevant recent incidents or safety alerts relating to CoW?",
        "Are sites identifying gaps in permit quality or compliance through audits? And are they recorded and actioned, tracked to completion?",
    ]),
]

TBT_SECTIONS = [
    ("1. TBT Hazard Identification", [
        "TBT Lead (typically the PA) discusses the hazards and controls associated to the task/activity (sourced from the Task Risk Assessment).",
        "SIMOP activities that may conflict with the activity / task?",
        "Spills, and potential proximity to open drains discussed and how they can be avoided?",
        "Situation awareness, such as potential dropped objects (tools, equipment or structural) discussed and actions taken?",
        "Isolations, identified checked and discussed?",
        "Emergency response arrangements been discussed and everyone understands what to do?",
        "Where additional significant hazards are identified, is the job stopped and reported to the AA for the TRA to be reassessed and re-authorised?",
        "Is the TBT used for its intention i.e. discuss task details by reviewing the identified energy prompts in the RA and control measures, review key supporting documentation and record MINOR additional hazards?",
    ]),
    ("2. TBT Understanding the Task", [
        "Are questions open to engage the work party?",
        "Is the activity broken down into significant steps?",
        "How is the team undertaking each step? Is the method clear?",
        "Has the work party actively participated in the safety toolbox talk discussion and signed the TBT?",
        "Where there is a Lone Work party, confirm that the PA has completed the TBT with the Area Authority (AA) prior to commencing the task.",
    ]),
    ("3. Hazards associated to the Worksite and Equipment", [
        "Have tools and equipment been clearly identified on the risk assessment and adequate controls in place?",
        "Are there any additional hazards transporting tools and equipment to the work site?",
        "Are all access and egress points checked and clear?",
    ]),
    ("4. Permit Compliance", [
        "Is there an up-to-date copy of the WCC at the worksite and signed by all members of the work party?",
        "Is the permit (New or Routine) specific for the task and not generic?",
        "Is the task broken down into clearly defined steps and details the sequence in which it will be done?",
    ]),
    ("5. Permit Compliance - Implementing the Controls", [
        "If required, have gas tests been carried out and recorded on the permit? And a gas detector available if required?",
        "Have all controls on the permit been implemented?",
        "Have controls within supplementary risk evaluation such as COSHH, Manual Handling, HAVS, BOC checks etc. been implemented and the team is aware?",
        "Where substances are in use, does the work party understand what action to take in an emergency?",
        "Have additional method statements been reviewed, recorded and complied with?",
    ]),
    ("6. Permit Authorisation", [
        "Has the permit undergone the correct level of authorisation? AA and Site Controller?",
        "For NUI’s – Have all Level 2 risk assessment activities been discussed with the hub OIM prior to authorisation and issue?",
    ]),
    ("7. Managing ‘Low Risk’ activities", [
        "Is the routine WCC suitable and specific for the task and appropriate to justify ‘low risk’?",
        "Those tasks which do not require a permit i.e. routine helideck ops etc., has a TBT been completed?",
    ]),
]

POP_SECTION = ("8. Process Operating Procedures (POP)", [
    "Has a TBT been completed prior to work commencing?",
    "Is the POP being followed in the correct sequence? Valve line up completed (where appropriate)?",
    "Two person signatures applied for critical steps?",
    "Are operators using the most up to date POP’s – check how controlled documents are managed?",
    "Is the POP in its review date? And has it been transferred to the new format (i.e. Task screening assessment)?",
    "Are completed POP’s scanned and uploaded to a designated storage area?",
    "Is the handover section signed at the end of the shift and countersigned by incoming and outgoing OTL?",
])

if "submissions" not in st.session_state:
    st.session_state.submissions = []
if "responses" not in st.session_state:
    st.session_state.responses = []


def qkey(prefix: str, idx: int, suffix: str) -> str:
    return f"{prefix}_{idx}_{suffix}"


def render_question(prefix: str, idx: int, question: str, action_required_on_no: bool = True):
    review = QUESTION_REVIEW_FLAGS.get(question)
    if review:
        reason, suggestion = review
        html = f"""<div style='border:2px solid #d32f2f;background:#fff1f1;padding:12px 14px;border-radius:8px;margin:6px 0 8px 0;'>
        <div style='font-weight:700;color:#b71c1c;font-size:1.02rem;'>⚠ REVIEW REQUIRED — {idx}. {question}</div>
        <div style='color:#b71c1c;margin-top:6px;'><b>Why flagged:</b> {reason}</div>
        <div style='color:#7f0000;margin-top:4px;'><b>Suggested wording:</b> {suggestion}</div>
        </div>"""
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(f"**{idx}. {question}**")
    c1, c2 = st.columns([1.1, 4])
    response = c1.selectbox("Confirm", RESPONSE_OPTIONS, key=qkey(prefix, idx, "response"), label_visibility="collapsed")
    evidence = c2.text_input("Comments / Evidence", key=qkey(prefix, idx, "evidence"), placeholder="Comments / evidence", label_visibility="collapsed")
    action = owner = ""
    due = None
    if response == "No" and action_required_on_no:
        a1, a2, a3 = st.columns([3.6, 1.5, 1.2])
        action = a1.text_input("SMART Action", key=qkey(prefix, idx, "action"), placeholder="SMART action required")
        owner = a2.text_input("Action owner", key=qkey(prefix, idx, "owner"), placeholder="Owner")
        due = a3.date_input("Due date", key=qkey(prefix, idx, "due"), value=date.today() + timedelta(days=30))
    st.divider()
    return {"question_no": idx, "question": question, "response": response, "comments_evidence": evidence,
            "smart_action": action, "action_owner": owner, "due_date": str(due) if due else ""}


def save_submission(form_name: str, metadata: dict, responses: list[dict], extras: dict | None = None):
    audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    complete = [r for r in responses if r["response"] in ("Yes", "No", "N/A")]
    yes = sum(r["response"] == "Yes" for r in complete)
    no = sum(r["response"] == "No" for r in complete)
    na = sum(r["response"] == "N/A" for r in complete)
    applicable = yes + no
    conformance = round((yes / applicable * 100), 1) if applicable else None
    header = {
        "audit_id": audit_id, "form_name": form_name, **metadata,
        "yes": yes, "no": no, "na": na, "conformance_pct": conformance,
        "overall_standard": "Does not meet CoW Standard" if no else "Meets CoW Standard",
    }
    if extras:
        header.update(extras)
    st.session_state.submissions.append(header)
    for r in responses:
        st.session_state.responses.append({"audit_id": audit_id, "form_name": form_name, **r})
    return audit_id, header


def required_check(responses):
    unanswered = [r for r in responses if not r["response"]]
    missing_actions = [r for r in responses if r["response"] == "No" and not r["smart_action"].strip()]
    return unanswered, missing_actions


st.sidebar.title("PUK CoW Assurance")
st.sidebar.caption("Streamlit data-capture prototype")
page = st.sidebar.radio("Go to", ["Home", "Permit Quality", "Leadership Engagement", "TBT / Permit / POP", "Submitted Audits"], label_visibility="collapsed")

st.title("Control of Work Assurance")
st.caption("Digital versions of the three supplied assurance checklists. Prototype data remains in the current Streamlit session only.")
st.markdown("<span style='color:#b71c1c;font-weight:700;'>Red questions are flagged because the Yes/No/N/A response could be reversed, conditional, compound or otherwise confusing for conformance scoring.</span>", unsafe_allow_html=True)

if page == "Home":
    st.subheader("Assurance forms")
    st.write("Select a form from the left-hand menu. Each form preserves the supplied Word checklist structure and records Yes / No / N/A, comments/evidence and a SMART action where a non-conformance is identified.")
    c1, c2, c3 = st.columns(3)
    c1.info("**Level 4 – Permit Quality**\n\nPermit/WCC quality and risk-assessment review.")
    c2.info("**Leadership Engagement**\n\nVisible leadership and workforce engagement checklist.")
    c3.info("**Level 4 – TBT / Permit / POP**\n\nSite visit, TBT and worksite compliance review with POP branch.")
    st.warning("For testing only: submissions are not yet written to Snowflake or another persistent database. Use the export page before the session is reset.")

elif page == "Permit Quality":
    st.header("SELF VERIFICATION – LEVEL 4 MONITORING")
    st.subheader("Control of Work: Permit Quality")
    st.info("Purpose: This monitoring activity is intended to verify day-to-day compliance with Permit-to-Work requirements, ensuring that permits and supporting risk assessments are suitable and sufficient for the task, safe working practices are consistently applied, and gaps in knowledge or understanding that could lead to hazardous errors are identified and addressed. The activity is designed for leadership roles (AA, Site Controller, Asset Superintendent) to strengthen oversight, promote engagement, and provide leadership assurance of Permit-to-Work effectiveness.")

    c1, c2, c3 = st.columns(3)
    site = c1.selectbox("SITE / INSTALLATION", SITES)
    team = c2.text_input("TEAM")
    audit_date = c3.date_input("DATE OF AUDIT", value=date.today())
    c1, c2, c3 = st.columns(3)
    wcc_type = c1.radio("WCC TYPE", ["New WCC", "Routine"], horizontal=True)
    site_controller = c2.text_input("SITE CONTROLLER")
    auditor = c3.text_input("AUDITOR")
    c1, c2 = st.columns(2)
    wcc_no = c1.text_input("WCC NUMBER")
    description = c2.text_input("WCC DESCRIPTION")

    responses, qn = [], 1
    for section, questions in PERMIT_SECTIONS:
        with st.expander(section, expanded=True):
            for q in questions:
                r = render_question("permit", qn, q)
                r["section"] = section
                responses.append(r)
                qn += 1

    if st.button("Save Permit Quality Audit", type="primary", use_container_width=True):
        unanswered, missing = required_check(responses)
        if unanswered:
            st.error(f"Complete all questions before saving. {len(unanswered)} response(s) are blank.")
        elif missing:
            st.error(f"Each 'No' requires a SMART action. {len(missing)} action(s) are missing.")
        else:
            audit_id, header = save_submission("Permit Quality", {
                "date": str(audit_date), "site": site, "team": team, "wcc_type": wcc_type,
                "site_controller": site_controller, "auditor": auditor, "reference": wcc_no,
                "description": description
            }, responses)
            st.success(f"Saved {audit_id} • {header['overall_standard']} • {header['conformance_pct']}% conformance")

elif page == "Leadership Engagement":
    st.header("Control of Work Leadership Engagement Checklist")
    st.info("Purpose: This checklist provides a predefined set of Control of Work questions for leadership engagement visits. It supports visible leadership, workforce engagement and assurance discussions covering permit quality, hazard awareness, implementation of controls, supervision, Stop the Job culture and learning opportunities.")

    c1, c2 = st.columns(2)
    audit_date = c1.date_input("Date", value=date.today(), key="lead_date")
    location_team = c2.text_input("Location / Team (add W2W N/S or Flying N/S)")
    c1, c2 = st.columns(2)
    site_controller = c1.text_input("Site Controller", key="lead_sc")
    leader = c2.text_input("Leadership Representative")

    responses, qn = [], 1
    for section, questions in LEADERSHIP_SECTIONS:
        with st.expander(section, expanded=True):
            for q in questions:
                r = render_question("lead", qn, q)
                r["section"] = section
                responses.append(r)
                qn += 1

    st.subheader("Learning & Continuous Improvement – workforce suggestion")
    improvement = st.text_area("Can personnel suggest any improvements to the Control of Work process?")

    st.subheader("Leadership Summary")
    positive = st.text_area("Positive Observations")
    opportunities = st.text_area("Opportunities for Improvement")
    actions_agreed = st.text_area("Actions Agreed")
    auditor_notes = st.text_area("Auditor Notes")

    st.caption("Source rule: if one question is deemed ‘No’ or non-conformance, mark the audit as ‘Does not meet CoW Standard’. Where N/A is appropriate, record it with supporting comments/evidence.")

    if st.button("Save Leadership Engagement", type="primary", use_container_width=True):
        unanswered, missing = required_check(responses)
        if unanswered:
            st.error(f"Complete all questions before saving. {len(unanswered)} response(s) are blank.")
        elif missing:
            st.error(f"Each 'No' requires a SMART action. {len(missing)} action(s) are missing.")
        else:
            audit_id, header = save_submission("Leadership Engagement", {
                "date": str(audit_date), "site": location_team, "team": location_team,
                "site_controller": site_controller, "auditor": leader, "reference": "", "description": ""
            }, responses, {
                "workforce_improvement": improvement, "positive_observations": positive,
                "opportunities_for_improvement": opportunities, "actions_agreed": actions_agreed,
                "auditor_notes": auditor_notes
            })
            st.success(f"Saved {audit_id} • {header['overall_standard']} • {header['conformance_pct']}% conformance")

elif page == "TBT / Permit / POP":
    st.header("SELF VERIFICATION – LEVEL 4 MONITORING")
    st.subheader("Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures")
    st.info("Purpose: This monitoring activity is intended to be used to self-verify the day-to-day compliance of TBT & Permits Compliance, ensuring the TBT is suitable for the tasks outlined in the permit and operating procedure, reinforcing safe working practices and identifying gaps in team knowledge that could lead to hazardous mistakes. This assurance activity is designed for leadership roles (HSEA, OTL, W2W OOE & Site Controller) to strengthen oversight, promote engagement, and provide leadership assurance of Permit-to-Work effectiveness.")
    st.warning("Site Visit is Required – Sequential Review: TBT followed by Permit Compliance or POP")

    c1, c2, c3 = st.columns(3)
    site = c1.selectbox("SITE / INSTALLATION", SITES, key="tbt_site")
    team = c2.text_input("TEAM", key="tbt_team")
    audit_date = c3.date_input("DATE OF AUDIT", value=date.today(), key="tbt_date")
    c1, c2, c3 = st.columns(3)
    activity_type = c1.radio("ACTIVITY TYPE", ["New WCC", "Routine", "POP"], horizontal=True)
    auditor = c2.text_input("AUDITOR", key="tbt_auditor")
    site_controller = c3.text_input("SITE CONTROLLER", key="tbt_sc")
    c1, c2 = st.columns(2)
    ref = c1.text_input("WCC / POP No")
    description = c2.text_input("DESCRIPTION")

    responses, qn = [], 1
    # Questions 1-2 always apply. If auditing POP, source form says move to Q8 after Q2.
    base_sections = TBT_SECTIONS[:2] if activity_type == "POP" else TBT_SECTIONS
    for section, questions in base_sections:
        with st.expander(section, expanded=True):
            for q in questions:
                r = render_question("tbt", qn, q)
                r["section"] = section
                responses.append(r)
                qn += 1

    if activity_type == "POP":
        st.info("POP selected: following the source form, questions 3–7 are skipped and the review moves to question 8.")
        section, questions = POP_SECTION
        with st.expander(section, expanded=True):
            for q in questions:
                r = render_question("tbt_pop", qn, q)
                r["section"] = section
                responses.append(r)
                qn += 1

    if st.button("Save TBT / Permit / POP Audit", type="primary", use_container_width=True):
        unanswered, missing = required_check(responses)
        if unanswered:
            st.error(f"Complete all questions before saving. {len(unanswered)} response(s) are blank.")
        elif missing:
            st.error(f"Each 'No' requires a SMART action. {len(missing)} action(s) are missing.")
        else:
            audit_id, header = save_submission("TBT / Permit / POP", {
                "date": str(audit_date), "site": site, "team": team, "activity_type": activity_type,
                "site_controller": site_controller, "auditor": auditor, "reference": ref,
                "description": description
            }, responses)
            st.success(f"Saved {audit_id} • {header['overall_standard']} • {header['conformance_pct']}% conformance")

elif page == "Submitted Audits":
    st.header("Submitted Audits")
    if not st.session_state.submissions:
        st.info("No audits have been saved in this session yet.")
    else:
        headers = pd.DataFrame(st.session_state.submissions)
        detail = pd.DataFrame(st.session_state.responses)
        st.dataframe(headers, use_container_width=True, hide_index=True)
        st.subheader("Question-level responses")
        st.dataframe(detail, use_container_width=True, hide_index=True)

        c1, c2, c3 = st.columns(3)
        c1.download_button("Download audit summary CSV", headers.to_csv(index=False).encode("utf-8"), "puk_audit_summary.csv", "text/csv", use_container_width=True)
        c2.download_button("Download question responses CSV", detail.to_csv(index=False).encode("utf-8"), "puk_audit_responses.csv", "text/csv", use_container_width=True)
        payload = {"audits": st.session_state.submissions, "responses": st.session_state.responses}
        c3.download_button("Download JSON", json.dumps(payload, indent=2, default=str), "puk_assurance_export.json", "application/json", use_container_width=True)

        st.caption("The two CSV outputs are intentionally separated into an audit-header table and a question-response table. This structure is suitable for feeding the existing HTML dashboard now and Snowflake later.")
