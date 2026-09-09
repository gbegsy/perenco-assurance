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


# BAR classification used in this review version.
# BAR indicates the importance of the control, not the severity of a finding.
BAR_DEFINITIONS = {
    "BAR 1": "Critical control – directly linked to preventing a major accident, serious harm or loss of containment.",
    "BAR 2": "Key operational control – supports safe task execution and prevents significant incidents.",
    "BAR 3": "Supporting control – planning, administrative or good-practice control that strengthens the overall framework.",
}

# Question-level BAR allocation. Keys use the form prefix and displayed question number.
BAR_BY_QUESTION = {
    "permit": {
        1:"BAR 3",2:"BAR 3",3:"BAR 3",4:"BAR 1",5:"BAR 2",6:"BAR 2",7:"BAR 2",8:"BAR 2",9:"BAR 2",10:"BAR 1",
        11:"BAR 2",12:"BAR 2",13:"BAR 1",14:"BAR 2",15:"BAR 1",16:"BAR 1",17:"BAR 2",18:"BAR 1",19:"BAR 2",20:"BAR 1",
        21:"BAR 2",22:"BAR 3",23:"BAR 2",24:"BAR 1",25:"BAR 2",26:"BAR 3"
    },
    "lead": {
        1:"BAR 2",2:"BAR 2",3:"BAR 2",4:"BAR 2",5:"BAR 1",6:"BAR 1",7:"BAR 1",8:"BAR 1",9:"BAR 1",10:"BAR 2",
        11:"BAR 2",12:"BAR 2",13:"BAR 2",14:"BAR 1",15:"BAR 1",16:"BAR 1",17:"BAR 1",18:"BAR 2",19:"BAR 3",20:"BAR 2",
        21:"BAR 2",22:"BAR 1",23:"BAR 2",24:"BAR 1",25:"BAR 1",26:"BAR 3",27:"BAR 3"
    },
    "tbt": {
        1:"BAR 1",2:"BAR 1",3:"BAR 2",4:"BAR 1",5:"BAR 1",6:"BAR 1",7:"BAR 1",8:"BAR 2",9:"BAR 2",10:"BAR 2",
        11:"BAR 2",12:"BAR 3",13:"BAR 2",14:"BAR 2",15:"BAR 2",16:"BAR 2",17:"BAR 2",18:"BAR 2",19:"BAR 2",20:"BAR 1",
        21:"BAR 1",22:"BAR 1",23:"BAR 1",24:"BAR 2",25:"BAR 1",26:"BAR 1",27:"BAR 2",28:"BAR 3"
    },
    # POP questions follow TBT questions 1–13 when POP is selected, so they display as 14–20.
    "tbt_pop": {14:"BAR 2",15:"BAR 1",16:"BAR 1",17:"BAR 3",18:"BAR 3",19:"BAR 3",20:"BAR 3"},
}

# Corrected live wording for questions identified as unsuitable or confusing for simple Yes/No/N/A scoring.
# These remain RED in this version so the changes are transparent during review.
CORRECTED_QUESTIONS = {
    "Is the activity planned to be undertaken outside the next 24 hours?": "Has the activity been planned in accordance with the required planning timescales and process?",
    "How is the team doing it? Is the method clear?": "Is the method for completing the task clearly described and understood?",
    "Does the activity involve breaking of containment on ANY system? And has a thorough hazard identification been conducted to evaluate the associated risks?": "Where breaking containment is involved, has a thorough hazard identification been completed and the associated risks adequately controlled?",
    "Has a team consisting of 3 persons (who have suitable knowledge of the task) taken part in the risk assessment? Is the task risk assessment team leader competent (check PCAP profile)?": "Has the risk assessment been completed by the required competent team, including a competent task risk assessment team leader?",
    "Is it clear what the hazard is and who/what might be harmed? Is there only one hazard per statement?": "Does each hazard statement clearly identify the hazard and who or what may be harmed, with one hazard per statement?",
    "Are Control Statements clear on who is doing what and when? Is there enough detail to make it clear but short and concise? Is it clear and simple language?": "Do the control statements clearly state who will do what and when, using clear, concise and unambiguous language?",
    "Is the risk reduction credible? Have considerations been made to ensure that for those who have been given numerous actions, the risk of error is not increased?": "Is the proposed risk reduction credible, with control responsibilities allocated so that action loading does not increase the risk of error?",
    "Is the WCC free from hazards and controls which do not actively reduce the risk OR are part of standardised measures already in place, i.e. standards / Standard PPE etc.?": "Does the WCC contain only task-relevant hazards and controls that actively reduce risk, excluding standard controls already covered elsewhere?",
    "Have any conditions changed since work commenced?": "Where conditions have changed since work commenced, has the work been stopped, reassessed and appropriately controlled before continuing?",
    "Have Major Accident Hazard (MAH) risks been considered where applicable?": "Where applicable, have relevant Major Accident Hazard (MAH) risks been identified and appropriately controlled?",
    "Are there any examples of conditions differing from those described in the permit?": "Do the actual worksite conditions match those described in the permit?",
    "Are there any barriers preventing personnel from raising concerns?": "Are personnel able to raise concerns or stop the work without barriers?",
    "Are sites identifying gaps in permit quality or compliance through audits? And are they recorded and actioned, tracked to completion?": "Are permit or compliance gaps identified through audits recorded, actioned and tracked to completion?",
    "TBT Lead (typically the PA) discusses the hazards and controls associated to the task/activity (sourced from the Task Risk Assessment).": "Has the TBT Lead discussed the task hazards and controls identified in the Task Risk Assessment with the work party?",
    "SIMOP activities that may conflict with the activity / task?": "Have relevant SIMOP activities that could conflict with the task been identified, discussed and appropriately controlled?",
    "Spills, and potential proximity to open drains discussed and how they can be avoided?": "Where relevant, have spill risks and proximity to open drains been discussed and appropriate controls agreed?",
    "Situation awareness, such as potential dropped objects (tools, equipment or structural) discussed and actions taken?": "Have relevant situational hazards, including potential dropped objects, been discussed and appropriate controls implemented?",
    "Isolations, identified checked and discussed?": "Have all required isolations been identified, verified and discussed with the work party?",
    "Emergency response arrangements been discussed and everyone understands what to do?": "Have emergency response arrangements been discussed and does the work party understand what to do in an emergency?",
    "How is the team undertaking each step? Is the method clear?": "Is the method for undertaking each significant task step clear and understood by the work party?",
    "Where there is a Lone Work party, confirm that the PA has completed the TBT with the Area Authority (AA) prior to commencing the task.": "For lone work, has the PA completed the TBT with the Area Authority before commencing the task?",
    "Are there any additional hazards transporting tools and equipment to the work site?": "Have hazards associated with transporting tools and equipment to the worksite been identified and adequately controlled?",
}


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


# ========================= FULL PERENCO ASSURANCE SYSTEM =========================
# Streamlit data capture + KPI dashboard + action management + Snowflake-ready data model.

from calendar import monthrange
from datetime import datetime
from io import StringIO

APP_VERSION = "0.9 Perenco pilot"

# Perenco CoW KPI plan defaults derived from the supplied KPI specification.
# These are editable in Assurance Plan. Weekly requirements are converted to monthly
# planning defaults using 4 weeks only as an initial planning placeholder; the user can
# set the exact planned count for each reporting month before KPI reporting.
KPI1_WEEKLY_TARGETS = {
    "Dimlington": {"Routine": 1, "New WCC": 1},
    "Cleeton": {"Routine": 1, "New WCC": 1},
    "Ravenspurn North": {"Routine": 1, "New WCC": 1},
    "Northern NUI's": {"Routine": 2, "New WCC": 1},
    "Bacton": {"Routine": 1, "New WCC": 1},
    "Leman 27BC": {"Routine": 1, "New WCC": 1},
    "Southern NUI's": {"Routine": 2, "New WCC": 1},
}

LEADERSHIP_ROLES = [
    "Operations Director", "Deputy Operations Director", "Asset Superintendent",
    "Ops Support Manager", "Other"
]
PERMIT_ASSURANCE_ROLES = ["Site Controller", "Asset Superintendent", "Other"]
TBT_VISIT_ROLES = ["W2W OOE", "Medic/HSEA", "Field Hub OIM", "Site Controller", "Other"]
ACTION_STATUSES = ["Open", "In Progress", "Pending Verification", "Closed", "Transferred to Corporate AMS"]
ACTION_PRIORITIES = ["Immediate", "High", "Normal"]
INCIDENT_TYPES = ["Injury", "Loss of Containment", "Process Safety", "Near Miss", "Other"]

# Short display labels for final operational version. Full definitions are shown once on Home/Method.
BAR_SHORT = {"BAR 1":"BAR 1", "BAR 2":"BAR 2", "BAR 3":"BAR 3"}


def init_state():
    defaults = {
        "submissions": [], "responses": [], "incidents": [], "plans": [],
        "demo_loaded": False, "last_saved": None,
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def storage_mode():
    try:
        return str(st.secrets.get("storage", {}).get("mode", "session")).lower()
    except Exception:
        return "session"


def snowflake_enabled():
    return storage_mode() == "snowflake"


def sf_execute(sql: str, params=None):
    """Execute only when Perenco IT has configured Streamlit/Snowflake secrets."""
    conn = st.connection("snowflake")
    # Streamlit SnowflakeConnection exposes session() in Snowflake-hosted Streamlit.
    session = conn.session()
    q = session.sql(sql, params=params or [])
    return q.collect()


def persist_to_snowflake(header: dict, responses: list[dict]):
    if not snowflake_enabled():
        return
    # Deliberately explicit columns: easy for Perenco IT to map to corporate action management.
    sf_execute(
        """INSERT INTO COW_AUDITS
        (AUDIT_ID,FORM_NAME,AUDIT_DATE,SITE,TEAM,AUDITOR,ASSURANCE_ROLE,REFERENCE,DESCRIPTION,
         YES_COUNT,NO_COUNT,NA_COUNT,CONFORMANCE_PCT,OVERALL_STANDARD,CREATED_AT)
        SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP()""",
        [header.get(k,"") for k in ["audit_id","form_name","date","site","team","auditor","assurance_role","reference","description","yes","no","na","conformance_pct","overall_standard"]]
    )
    for r in responses:
        sf_execute(
            """INSERT INTO COW_RESPONSES
            (AUDIT_ID,FORM_NAME,QUESTION_NO,SECTION,QUESTION,ORIGINAL_QUESTION,BAR,RESPONSE,COMMENTS_EVIDENCE,
             SMART_ACTION,ACTION_OWNER,DUE_DATE,ACTION_STATUS,ACTION_PRIORITY,EXTERNAL_ACTION_ID)
            SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?""",
            [header["audit_id"], header["form_name"], r.get("question_no"), r.get("section",""), r.get("question",""),
             r.get("original_question",""), r.get("bar",""), r.get("response",""), r.get("comments_evidence",""),
             r.get("smart_action",""), r.get("action_owner",""), r.get("due_date",""), r.get("action_status","Open"),
             r.get("action_priority","Normal"), r.get("external_action_id","")]
        )


def qkey(prefix: str, idx: int, suffix: str) -> str:
    return f"{prefix}_{idx}_{suffix}"


def render_bar_badge(bar: str):
    # Only BAR number is shown against each live question to keep the form uncluttered.
    bg = {"BAR 1":"#8b1e2d", "BAR 2":"#b96b00", "BAR 3":"#2f5f73"}.get(bar,"#455a64")
    st.markdown(
        f"<span style='display:inline-block;background:{bg};color:white;font-weight:800;"
        f"padding:3px 9px;border-radius:13px;font-size:.78rem;margin:0 0 5px 0'>{bar}</span>",
        unsafe_allow_html=True,
    )


def render_question(prefix: str, idx: int, question: str, section: str):
    review = QUESTION_REVIEW_FLAGS.get(question)
    live_question = CORRECTED_QUESTIONS.get(question, question)
    bar = BAR_BY_QUESTION.get(prefix, {}).get(idx, "BAR 3")

    render_bar_badge(bar)
    if review:
        reason, _ = review
        # Corrected questions remain red in this Perenco review build, as requested.
        st.markdown(
            f"<div style='border-left:5px solid #c62828;background:#fff4f4;padding:10px 12px;border-radius:6px;margin-bottom:8px'>"
            f"<div style='font-weight:800;color:#b71c1c'>{idx}. {live_question}</div>"
            f"<details style='margin-top:6px;color:#7f0000'><summary>Source wording changed for clarity</summary>"
            f"<div style='margin-top:6px'><b>Original:</b> {question}</div>"
            f"<div><b>Reason:</b> {reason}</div></details></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"**{idx}. {live_question}**")

    c1,c2 = st.columns([1.15,4])
    response = c1.selectbox("Confirm", RESPONSE_OPTIONS, key=qkey(prefix,idx,"response"), label_visibility="collapsed")
    evidence = c2.text_input("Comments / Evidence", key=qkey(prefix,idx,"evidence"), placeholder="Comments / evidence", label_visibility="collapsed")
    action=owner=""; due=""; status=""; priority=""; external=""
    if response == "No":
        st.caption("A No is a recorded assurance gap. Add evidence and a SMART action.")
        a1,a2,a3 = st.columns([3.4,1.5,1.2])
        action = a1.text_input("SMART Action", key=qkey(prefix,idx,"action"), placeholder="Specific corrective action")
        owner = a2.text_input("Action owner", key=qkey(prefix,idx,"owner"), placeholder="Owner")
        due_val = a3.date_input("Due date", key=qkey(prefix,idx,"due"), value=date.today()+timedelta(days=30))
        due = str(due_val)
        b1,b2 = st.columns([1.2,2.8])
        priority = b1.selectbox("Priority", ACTION_PRIORITIES, index=0 if bar=="BAR 1" else 1 if bar=="BAR 2" else 2, key=qkey(prefix,idx,"priority"))
        external = b2.text_input("Corporate action ID (when transferred)", key=qkey(prefix,idx,"external"), placeholder="Optional")
        status = "Open"
    st.divider()
    return {
        "question_no": idx, "section": section, "question": live_question,
        "original_question": question if review else "", "bar": bar, "response": response,
        "comments_evidence": evidence, "smart_action": action, "action_owner": owner,
        "due_date": due, "action_status": status, "action_priority": priority,
        "external_action_id": external,
    }


def required_check(responses):
    unanswered=[r for r in responses if not r["response"]]
    missing_evidence=[r for r in responses if r["response"]=="No" and not r["comments_evidence"].strip()]
    missing_actions=[r for r in responses if r["response"]=="No" and not r["smart_action"].strip()]
    missing_owner=[r for r in responses if r["response"]=="No" and not r["action_owner"].strip()]
    return unanswered, missing_evidence, missing_actions, missing_owner


def save_submission(form_name: str, metadata: dict, responses: list[dict], extras=None):
    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}"
    complete=[r for r in responses if r["response"] in ("Yes","No","N/A")]
    yes=sum(r["response"]=="Yes" for r in complete); no=sum(r["response"]=="No" for r in complete); na=sum(r["response"]=="N/A" for r in complete)
    applicable=yes+no
    conformance=round(100*yes/applicable,1) if applicable else None
    bar1_fail=sum(r["response"]=="No" and r["bar"]=="BAR 1" for r in complete)
    bar2_fail=sum(r["response"]=="No" and r["bar"]=="BAR 2" for r in complete)
    bar3_fail=sum(r["response"]=="No" and r["bar"]=="BAR 3" for r in complete)
    header={"audit_id":audit_id,"form_name":form_name,**metadata,"yes":yes,"no":no,"na":na,
            "conformance_pct":conformance,"bar1_failures":bar1_fail,"bar2_failures":bar2_fail,"bar3_failures":bar3_fail,
            "overall_standard":"Does not meet CoW Standard" if no else "Meets CoW Standard",
            "created_at":datetime.now().isoformat(timespec="seconds")}
    if extras: header.update(extras)
    st.session_state.submissions.append(header)
    saved=[]
    for r in responses:
        rr={"audit_id":audit_id,"form_name":form_name,**r}
        st.session_state.responses.append(rr); saved.append(rr)
    st.session_state.last_saved=audit_id
    if snowflake_enabled():
        try: persist_to_snowflake(header, responses)
        except Exception as e: st.warning(f"Saved in current app session, but Snowflake write failed: {e}")
    return audit_id,header


def df_headers():
    return pd.DataFrame(st.session_state.submissions)

def df_responses():
    return pd.DataFrame(st.session_state.responses)

def df_actions():
    r=df_responses()
    if r.empty or "smart_action" not in r: return pd.DataFrame()
    a=r[r["smart_action"].fillna("").astype(str).str.strip()!=""].copy()
    if a.empty: return a
    cols=["audit_id","form_name","question_no","bar","question","smart_action","action_owner","due_date","action_status","action_priority","external_action_id","comments_evidence"]
    for c in cols:
        if c not in a: a[c]=""
    return a[cols]


def parse_date_series(s):
    return pd.to_datetime(s, errors="coerce")


def filtered_data(period_start, period_end, sites, auditors, forms):
    h=df_headers(); r=df_responses()
    if h.empty: return h,r
    h=h.copy(); h["_date"]=parse_date_series(h["date"])
    mask=(h["_date"].dt.date>=period_start)&(h["_date"].dt.date<=period_end)
    if sites: mask &= h["site"].isin(sites)
    if auditors: mask &= h["auditor"].isin(auditors)
    if forms: mask &= h["form_name"].isin(forms)
    h=h[mask]
    if r.empty: return h,r
    r=r[r["audit_id"].isin(h["audit_id"])]
    return h,r


def compliance(responses: pd.DataFrame):
    if responses.empty or "response" not in responses: return None
    y=(responses.response=="Yes").sum(); n=(responses.response=="No").sum()
    return round(100*y/(y+n),1) if y+n else None


def rag_status(completion, conform):
    if completion is None or conform is None: return "Not enough data"
    if completion>=100 and conform>=90: return "Green"
    if completion>=70 and conform>=70: return "Amber"
    return "Red"


def kpi_card(title, value, status, detail):
    colors={"Green":"#198754","Amber":"#d98200","Red":"#c83737","Not enough data":"#657489"}
    c=colors.get(status,"#657489")
    st.markdown(f"""<div style='background:#fff;border:1px solid #d9e3ec;border-left:6px solid {c};border-radius:10px;padding:12px;min-height:142px'>
    <div style='font-size:.78rem;color:#657489;font-weight:800;text-transform:uppercase'>{title}</div>
    <div style='font-size:1.7rem;font-weight:850;margin:7px 0'>{value}</div>
    <div style='display:inline-block;background:{c}18;color:{c};font-weight:800;border-radius:12px;padding:3px 8px'>{status}</div>
    <div style='font-size:.8rem;color:#657489;margin-top:8px'>{detail}</div></div>""",unsafe_allow_html=True)


def default_plan_rows(month_str):
    rows=[]
    for site,types in KPI1_WEEKLY_TARGETS.items():
        rows.append({"month":month_str,"kpi":"KPI 1","site":site,"role":"Site Controller","planned":4*sum(types.values())})
    rows.append({"month":month_str,"kpi":"KPI 2","site":"All","role":"Asset Superintendent","planned":4})
    rows.append({"month":month_str,"kpi":"KPI 3","site":"All","role":"Onshore Operations Leadership Team","planned":1}) # monthly planning view; formal KPI is 3/quarter
    rows.append({"month":month_str,"kpi":"KPI 4","site":"All","role":"W2W OOE","planned":4})
    rows.append({"month":month_str,"kpi":"KPI 4","site":"All","role":"Medic/HSEA","planned":4})
    rows.append({"month":month_str,"kpi":"KPI 4","site":"All","role":"Field Hub OIM","planned":0}) # quarter target managed in dashboard
    return rows


def plan_for(kpi, month_str, site=None):
    p=pd.DataFrame(st.session_state.plans)
    if p.empty: return None
    x=p[(p["month"]==month_str)&(p["kpi"]==kpi)]
    if site and "site" in x and site!="All": x=x[(x["site"]==site)|(x["site"]=="All")]
    return int(pd.to_numeric(x.get("planned",0),errors="coerce").fillna(0).sum()) if len(x) else None


def leadership_narrative(h,r,actions):
    if h.empty: return ("No assurance records are available for the selected period.","No evidence-based conclusion can yet be drawn.","Confirm the planned assurance activity and complete the scheduled reviews.")
    conf=compliance(r); b1=((r.get("bar",pd.Series(dtype=str))=="BAR 1")&(r.get("response",pd.Series(dtype=str))=="No")).sum() if not r.empty else 0
    no=(r.get("response",pd.Series(dtype=str))=="No").sum() if not r.empty else 0
    overdue=0
    if not actions.empty:
        d=pd.to_datetime(actions["due_date"],errors="coerce")
        overdue=((d<pd.Timestamp.today().normalize())&~actions["action_status"].isin(["Closed","Transferred to Corporate AMS"])).sum()
    seeing=f"{len(h)} assurance activities were recorded with {conf if conf is not None else '—'}% applicable-question conformance, including {int(no)} non-conformances and {int(b1)} BAR 1 failure(s)."
    meaning=("Critical-control assurance requires leadership attention; the aggregate percentage must not mask BAR 1 failures." if b1 else
             "No BAR 1 failures are visible in the selected evidence; continue to review recurring BAR 2/3 gaps and coverage.")
    action=(f"Prioritise verification and closure of {int(b1)} BAR 1 action(s) and {int(overdue)} overdue action(s)." if b1 or overdue else
            "Maintain planned coverage, verify action effectiveness and target repeat or deteriorating themes.")
    return seeing,meaning,action


def load_demo():
    if st.session_state.demo_loaded: return
    today=date.today()
    # Minimal clearly-labelled synthetic data to exercise the dashboard.
    forms=[
        ("Permit Quality","Dimlington","Site Controller",92.0,0,1,0),
        ("Permit Quality","Cleeton","Site Controller",86.0,1,1,0),
        ("Permit Quality","Ravenspurn North","Asset Superintendent",94.0,0,1,0),
        ("Leadership Engagement","Northern W2W","Operations Director",88.0,1,1,0),
        ("TBT / Permit / POP","Northern NUI's","W2W OOE",91.0,0,1,0),
    ]
    for i,(form,site,role,conf,b1,b2,b3) in enumerate(forms,1):
        aid=f"DEMO-{i:03d}"
        no=b1+b2+b3; yes=max(1,round((conf/100)*25));
        st.session_state.submissions.append({"audit_id":aid,"form_name":form,"date":str(today-timedelta(days=i*3)),"site":site,"team":"Demo team","auditor":f"Demo Auditor {i}","assurance_role":role,"reference":f"DEMO-{i}","description":"Synthetic demonstration record","yes":yes,"no":no,"na":1,"conformance_pct":conf,"bar1_failures":b1,"bar2_failures":b2,"bar3_failures":b3,"overall_standard":"Does not meet CoW Standard" if no else "Meets CoW Standard","created_at":datetime.now().isoformat(timespec="seconds")})
        # create simple detail preserving BAR failures
        for j in range(1,6):
            bar="BAR 1" if j<=b1 else "BAR 2" if j<=b1+b2 else "BAR 3"
            resp="No" if j<=no else "Yes"
            st.session_state.responses.append({"audit_id":aid,"form_name":form,"question_no":j,"section":"Demo","question":f"Synthetic question {j}","original_question":"","bar":bar,"response":resp,"comments_evidence":"Synthetic demonstration evidence","smart_action":f"Demo action {j}" if resp=="No" else "","action_owner":"Demo Owner" if resp=="No" else "","due_date":str(today+timedelta(days=20)) if resp=="No" else "","action_status":"Open" if resp=="No" else "","action_priority":"Immediate" if bar=="BAR 1" and resp=="No" else "Normal","external_action_id":""})
    st.session_state.demo_loaded=True


init_state()

# ----------------------------- NAVIGATION ---------------------------------
st.sidebar.title("PUK CoW Assurance")
st.sidebar.caption(f"Integrated Streamlit pilot • {APP_VERSION}")
page=st.sidebar.radio("Go to",[
    "Dashboard","Permit Quality","Leadership Engagement","TBT / Permit / POP",
    "Actions","KPI 5 Incidents","Assurance Plan","Submitted Audits","Data Admin","Method & BAR"
],label_visibility="collapsed")

if snowflake_enabled():
    st.sidebar.success("Storage: Snowflake")
else:
    st.sidebar.info("Storage: prototype session")

st.title("Control of Work Assurance")
st.caption("Perenco UK pilot • Streamlit data capture, BAR-classified assurance, KPI reporting and action workflow")

# ----------------------------- DASHBOARD ----------------------------------
if page=="Dashboard":
    st.header("Control of Work KPI Dashboard")
    if not st.session_state.submissions:
        st.info("No audit records are loaded. Complete an assurance form or use Data Admin → Load synthetic demonstration data to test the dashboard.")
    today=date.today(); month_start=today.replace(day=1); month_end=today.replace(day=monthrange(today.year,today.month)[1])
    c1,c2,c3,c4=st.columns(4)
    period=c1.selectbox("Period",["Current month","Rolling 3 months","Rolling 12 months","Custom"])
    if period=="Current month": start,end=month_start,month_end
    elif period=="Rolling 3 months": start,end=today-timedelta(days=90),today
    elif period=="Rolling 12 months": start,end=today-timedelta(days=365),today
    else:
        start=c1.date_input("From",today-timedelta(days=30)); end=c2.date_input("To",today)
    h0=df_headers()
    sites=sorted(h0["site"].dropna().astype(str).unique()) if not h0.empty and "site" in h0 else []
    auditors=sorted(h0["auditor"].dropna().astype(str).unique()) if not h0.empty and "auditor" in h0 else []
    forms=sorted(h0["form_name"].dropna().astype(str).unique()) if not h0.empty and "form_name" in h0 else []
    fs=c2.multiselect("Site / installation",sites)
    fa=c3.multiselect("Auditor",auditors)
    ff=c4.multiselect("Audit type",forms)
    h,r=filtered_data(start,end,fs,fa,ff)
    actions=df_actions();
    if not actions.empty and not h.empty: actions=actions[actions.audit_id.isin(h.audit_id)]

    # Overall assurance health and critical-bar visibility
    overall=compliance(r)
    b1fails=int(((r.get("bar",pd.Series(dtype=str))=="BAR 1")&(r.get("response",pd.Series(dtype=str))=="No")).sum()) if not r.empty else 0
    b2fails=int(((r.get("bar",pd.Series(dtype=str))=="BAR 2")&(r.get("response",pd.Series(dtype=str))=="No")).sum()) if not r.empty else 0
    b3fails=int(((r.get("bar",pd.Series(dtype=str))=="BAR 3")&(r.get("response",pd.Series(dtype=str))=="No")).sum()) if not r.empty else 0
    st.markdown(f"**Overall applicable-question conformance:** {overall if overall is not None else '—'}% &nbsp;&nbsp; | &nbsp;&nbsp; **BAR 1 failures:** {b1fails} &nbsp; **BAR 2:** {b2fails} &nbsp; **BAR 3:** {b3fails}")
    if b1fails: st.error("BAR 1 non-compliance is present. Critical-control failures remain visible regardless of aggregate KPI status.")

    month_str=f"{today.year}-{today.month:02d}"
    # KPI 1 / KPI 2 mappings
    pq=h[h.form_name=="Permit Quality"] if not h.empty else pd.DataFrame()
    pq_sc=pq[pq.get("assurance_role",pd.Series(index=pq.index,dtype=str))=="Site Controller"] if not pq.empty else pq
    pq_as=pq[pq.get("assurance_role",pd.Series(index=pq.index,dtype=str))=="Asset Superintendent"] if not pq.empty else pq
    r_sc=r[r.audit_id.isin(pq_sc.audit_id)] if not r.empty and not pq_sc.empty else pd.DataFrame()
    r_as=r[r.audit_id.isin(pq_as.audit_id)] if not r.empty and not pq_as.empty else pd.DataFrame()
    p1=plan_for("KPI 1",month_str); p2=plan_for("KPI 2",month_str)
    comp1=round(100*len(pq_sc)/p1,1) if p1 else None; conf1=compliance(r_sc); s1=rag_status(comp1,conf1)
    comp2=round(100*len(pq_as)/p2,1) if p2 else None; conf2=compliance(r_as); s2=rag_status(comp2,conf2)
    # KPI 3
    lead=h[h.form_name=="Leadership Engagement"] if not h.empty else pd.DataFrame(); rlead=r[r.audit_id.isin(lead.audit_id)] if not r.empty and not lead.empty else pd.DataFrame()
    qstart=date(today.year,3*((today.month-1)//3)+1,1); qend=date(qstart.year+(qstart.month+2>12),(qstart.month+2-1)%12+1,monthrange(qstart.year+(qstart.month+2>12),(qstart.month+2-1)%12+1)[1])
    leadq,_=filtered_data(qstart,qend,[],[],["Leadership Engagement"])
    v3=len(leadq); conf3=compliance(rlead); s3="Green" if v3>=3 and (conf3 is not None and conf3>=90) else "Amber" if v3>=2 and (conf3 is None or conf3>=70) else "Red"
    # KPI 4
    tbt=h[h.form_name=="TBT / Permit / POP"] if not h.empty else pd.DataFrame(); rtbt=r[r.audit_id.isin(tbt.audit_id)] if not r.empty and not tbt.empty else pd.DataFrame()
    p4=plan_for("KPI 4",month_str); comp4=round(100*len(tbt)/p4,1) if p4 else None; conf4=compliance(rtbt); s4=rag_status(comp4,conf4)
    # KPI 5
    inc=pd.DataFrame(st.session_state.incidents)
    rolling=prior=0; special=0
    if not inc.empty:
        inc["_date"]=pd.to_datetime(inc["date"],errors="coerce")
        now=pd.Timestamp(today); rolling=((inc._date>now-pd.Timedelta(days=365))&(inc._date<=now)).sum(); prior=((inc._date>now-pd.Timedelta(days=730))&(inc._date<=now-pd.Timedelta(days=365))).sum()
        current=inc[(inc._date>now-pd.Timedelta(days=365))&(inc._date<=now)]
        special=(current.get("hipo",False).astype(bool)|current.get("significant_injury",False).astype(bool)|current.get("loss_of_containment",False).astype(bool)).sum() if len(current) else 0
    s5="Red" if special>=2 else "Amber" if (rolling>prior or special==1) else "Green"

    cols=st.columns(5)
    with cols[0]: kpi_card("KPI 1 • Tier 3",f"{conf1 if conf1 is not None else '—'}%",s1,f"Site Controller permit quality • plan {len(pq_sc)}/{p1 if p1 is not None else 'not set'}")
    with cols[1]: kpi_card("KPI 2 • Tier 2",f"{conf2 if conf2 is not None else '—'}%",s2,f"Asset Superintendent permit quality • plan {len(pq_as)}/{p2 if p2 is not None else 'not set'}")
    with cols[2]: kpi_card("KPI 3 • Tier 2",f"{v3}/3",s3,f"Quarterly leadership engagements • {conf3 if conf3 is not None else '—'}% conformance")
    with cols[3]: kpi_card("KPI 4 • Tier 3",f"{conf4 if conf4 is not None else '—'}%",s4,f"Site leadership TBT/permit/POP • plan {len(tbt)}/{p4 if p4 is not None else 'not set'}")
    with cols[4]: kpi_card("KPI 5 • Tier 1",str(int(rolling)),s5,f"Permit-controlled incidents rolling 12m • prior {int(prior)}")

    st.subheader("Leadership Assurance Narrative")
    see,mean,act=leadership_narrative(h,r,actions)
    c1,c2,c3=st.columns(3); c1.info(f"**What are we seeing?**\n\n{see}"); c2.warning(f"**What does it mean?**\n\n{mean}"); c3.success(f"**What should leadership do?**\n\n{act}")

    c1,c2=st.columns(2)
    with c1:
        st.subheader("BAR performance")
        if r.empty: st.info("No question-level data in the selected period.")
        else:
            z=r[r.response.isin(["Yes","No"])].groupby(["bar","response"]).size().unstack(fill_value=0)
            for x in ["Yes","No"]:
                if x not in z: z[x]=0
            z["Conformance %"]=(100*z.Yes/(z.Yes+z.No)).round(1)
            st.dataframe(z[["Yes","No","Conformance %"]],use_container_width=True)
    with c2:
        st.subheader("Work as Imagined vs Work as Done")
        if r.empty: st.info("No evidence available.")
        else:
            keywords="worksite|permit|conditions|controls|method|understood|implemented"
            wa=r[r.question.str.contains(keywords,case=False,na=False)]
            gaps=wa[wa.response=="No"]
            if gaps.empty: st.success("No explicit Work-as-Done divergence identified in the selected question set.")
            else: st.dataframe(gaps[["audit_id","bar","question","comments_evidence"]],use_container_width=True,hide_index=True)

    st.subheader("Site / auditor assurance view")
    if not h.empty:
        view=h.groupby(["site","auditor"],dropna=False).agg(Audits=("audit_id","count"),Average_Conformance=("conformance_pct","mean"),BAR1_Failures=("bar1_failures","sum")).reset_index()
        st.dataframe(view,use_container_width=True,hide_index=True)

    st.subheader("Open assurance actions")
    if actions.empty: st.info("No actions in the selected data.")
    else: st.dataframe(actions[~actions.action_status.isin(["Closed"])],use_container_width=True,hide_index=True)

# ----------------------------- FORMS --------------------------------------
elif page=="Permit Quality":
    st.header("SELF VERIFICATION – LEVEL 4 MONITORING")
    st.subheader("Control of Work: Permit Quality")
    st.info("Purpose: Verify day-to-day Permit-to-Work quality and supporting risk assessment, safe working practices and control effectiveness.")
    c1,c2,c3=st.columns(3); site=c1.selectbox("SITE / INSTALLATION",SITES); team=c2.text_input("TEAM"); audit_date=c3.date_input("DATE OF AUDIT",value=date.today())
    c1,c2,c3=st.columns(3); wcc_type=c1.radio("WCC TYPE",["New WCC","Routine"],horizontal=True); role=c2.selectbox("ASSURANCE ROLE",PERMIT_ASSURANCE_ROLES); site_controller=c3.text_input("SITE CONTROLLER")
    c1,c2,c3=st.columns(3); auditor=c1.text_input("AUDITOR"); wcc_no=c2.text_input("WCC NUMBER"); description=c3.text_input("WCC DESCRIPTION")
    responses=[]; qn=1
    for section,questions in PERMIT_SECTIONS:
        with st.expander(section,expanded=True):
            for q in questions:
                responses.append(render_question("permit",qn,q,section)); qn+=1
    if st.button("Submit Permit Quality Audit",type="primary",use_container_width=True):
        u,e,a,o=required_check(responses)
        if u or e or a or o: st.error(f"Cannot submit: {len(u)} unanswered, {len(e)} No responses without evidence, {len(a)} actions missing, {len(o)} owners missing.")
        else:
            aid,h=save_submission("Permit Quality",{"date":str(audit_date),"site":site,"team":team,"wcc_type":wcc_type,"assurance_role":role,"site_controller":site_controller,"auditor":auditor,"reference":wcc_no,"description":description},responses)
            st.success(f"Submitted {aid} • {h['conformance_pct']}% • BAR 1 failures: {h['bar1_failures']}")

elif page=="Leadership Engagement":
    st.header("Control of Work Leadership Engagement Checklist")
    st.info("Visible leadership and workforce engagement covering permit quality, hazards, controls, supervision, Stop the Job culture and learning.")
    c1,c2=st.columns(2); audit_date=c1.date_input("Date",value=date.today(),key="lead_date"); location=c2.text_input("Location / Team (add W2W N/S or Flying N/S)")
    c1,c2,c3=st.columns(3); sc=c1.text_input("Site Controller",key="lead_sc"); leader=c2.text_input("Leadership Representative"); role=c3.selectbox("Leadership role",LEADERSHIP_ROLES)
    responses=[]; qn=1
    for section,questions in LEADERSHIP_SECTIONS:
        with st.expander(section,expanded=True):
            for q in questions:
                responses.append(render_question("lead",qn,q,section)); qn+=1
    improvement=st.text_area("Workforce improvement suggestion")
    c1,c2=st.columns(2); positive=c1.text_area("Positive Observations"); opportunities=c2.text_area("Opportunities for Improvement")
    actions_agreed=st.text_area("Actions Agreed"); notes=st.text_area("Auditor Notes")
    if st.button("Submit Leadership Engagement",type="primary",use_container_width=True):
        u,e,a,o=required_check(responses)
        if u or e or a or o: st.error(f"Cannot submit: {len(u)} unanswered, {len(e)} No responses without evidence, {len(a)} actions missing, {len(o)} owners missing.")
        else:
            aid,h=save_submission("Leadership Engagement",{"date":str(audit_date),"site":location,"team":location,"assurance_role":role,"site_controller":sc,"auditor":leader,"reference":"","description":""},responses,{"workforce_improvement":improvement,"positive_observations":positive,"opportunities_for_improvement":opportunities,"actions_agreed":actions_agreed,"auditor_notes":notes})
            st.success(f"Submitted {aid} • {h['overall_standard']} • {h['conformance_pct']}%")

elif page=="TBT / Permit / POP":
    st.header("SELF VERIFICATION – LEVEL 4 MONITORING")
    st.subheader("Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures")
    st.warning("Site Visit Required – sequential review: TBT followed by Permit Compliance or POP")
    c1,c2,c3=st.columns(3); site=c1.selectbox("SITE / INSTALLATION",SITES,key="tbt_site"); team=c2.text_input("TEAM",key="tbt_team"); audit_date=c3.date_input("DATE OF AUDIT",value=date.today(),key="tbt_date")
    c1,c2,c3=st.columns(3); activity=c1.radio("ACTIVITY TYPE",["New WCC","Routine","POP"],horizontal=True); role=c2.selectbox("VISIT / ASSURANCE ROLE",TBT_VISIT_ROLES); auditor=c3.text_input("AUDITOR",key="tbt_auditor")
    c1,c2,c3=st.columns(3); sc=c1.text_input("SITE CONTROLLER",key="tbt_sc"); ref=c2.text_input("WCC / POP No"); description=c3.text_input("DESCRIPTION")
    responses=[]; qn=1
    base=TBT_SECTIONS[:2] if activity=="POP" else TBT_SECTIONS
    for section,questions in base:
        with st.expander(section,expanded=True):
            for q in questions:
                responses.append(render_question("tbt",qn,q,section)); qn+=1
    if activity=="POP":
        st.info("POP selected: following the source form, Questions 3–7 are skipped and the review moves to Process Operating Procedures.")
        section,questions=POP_SECTION
        with st.expander(section,expanded=True):
            for q in questions:
                responses.append(render_question("tbt_pop",qn,q,section)); qn+=1
    if st.button("Submit TBT / Permit / POP Audit",type="primary",use_container_width=True):
        u,e,a,o=required_check(responses)
        if u or e or a or o: st.error(f"Cannot submit: {len(u)} unanswered, {len(e)} No responses without evidence, {len(a)} actions missing, {len(o)} owners missing.")
        else:
            aid,h=save_submission("TBT / Permit / POP",{"date":str(audit_date),"site":site,"team":team,"activity_type":activity,"assurance_role":role,"site_controller":sc,"auditor":auditor,"reference":ref,"description":description},responses)
            st.success(f"Submitted {aid} • {h['conformance_pct']}% • BAR 1 failures: {h['bar1_failures']}")

# ----------------------------- ACTIONS ------------------------------------
elif page=="Actions":
    st.header("Assurance Action Management")
    st.caption("Prototype action workflow. The External Action ID field is reserved for Perenco's corporate action-management system.")
    actions=df_actions()
    if actions.empty: st.info("No assurance actions have been generated yet. A No response in an audit creates an action.")
    else:
        c1,c2,c3=st.columns(3); fb=c1.multiselect("BAR",["BAR 1","BAR 2","BAR 3"]); fs=c2.multiselect("Status",ACTION_STATUSES); owner=c3.text_input("Owner contains")
        a=actions.copy()
        if fb: a=a[a.bar.isin(fb)]
        if fs: a=a[a.action_status.isin(fs)]
        if owner: a=a[a.action_owner.str.contains(owner,case=False,na=False)]
        edited=st.data_editor(a,use_container_width=True,hide_index=True,column_config={"action_status":st.column_config.SelectboxColumn("Status",options=ACTION_STATUSES),"action_priority":st.column_config.SelectboxColumn("Priority",options=ACTION_PRIORITIES)},disabled=["audit_id","form_name","question_no","bar","question","comments_evidence"],key="action_editor")
        if st.button("Save action updates",type="primary"):
            # Update session response records using audit_id + question_no as composite key.
            lookup={(str(row.audit_id),int(row.question_no)):row for _,row in edited.iterrows()}
            for rr in st.session_state.responses:
                key=(str(rr.get("audit_id")),int(rr.get("question_no",0)))
                if key in lookup:
                    row=lookup[key]
                    for c in ["smart_action","action_owner","due_date","action_status","action_priority","external_action_id"]: rr[c]=row[c]
            st.success("Action updates saved in the current app data store.")

# ----------------------------- INCIDENTS ----------------------------------
elif page=="KPI 5 Incidents":
    st.header("KPI 5 • Permit-Controlled Activity Incidents")
    st.caption("Manual prototype input for MOI data. In the Perenco environment this should be replaced by the approved MOI/Snowflake source.")
    with st.form("incident_form"):
        c1,c2,c3=st.columns(3); idate=c1.date_input("Incident date",date.today()); site=c2.selectbox("Site",SITES,key="inc_site"); itype=c3.selectbox("Incident type",INCIDENT_TYPES)
        desc=st.text_area("Description / event reference")
        c1,c2,c3=st.columns(3); hipo=c1.checkbox("HiPo"); sig=c2.checkbox("Significant injury (MTC or above)"); loc=c3.checkbox("Loss of containment")
        submitted=st.form_submit_button("Add incident",type="primary")
        if submitted:
            st.session_state.incidents.append({"incident_id":f"INC-{uuid.uuid4().hex[:7].upper()}","date":str(idate),"site":site,"incident_type":itype,"description":desc,"hipo":hipo,"significant_injury":sig,"loss_of_containment":loc})
            st.success("Incident record added.")
    if st.session_state.incidents: st.dataframe(pd.DataFrame(st.session_state.incidents),use_container_width=True,hide_index=True)

# ----------------------------- PLAN ---------------------------------------
elif page=="Assurance Plan":
    st.header("Assurance Plan / Coverage")
    st.caption("Set the planned monthly activity used by KPI 1, 2 and 4 completion calculations. KPI 3 retains the formal 3-per-quarter target.")
    m=st.text_input("Reporting month (YYYY-MM)",value=f"{date.today().year}-{date.today().month:02d}")
    if st.button("Create default plan for month"):
        existing={(x["month"],x["kpi"],x["site"],x["role"]) for x in st.session_state.plans}
        for row in default_plan_rows(m):
            k=(row["month"],row["kpi"],row["site"],row["role"])
            if k not in existing: st.session_state.plans.append(row)
        st.success("Default planning rows created. Review and edit the planned counts before relying on KPI completion status.")
    p=pd.DataFrame(st.session_state.plans)
    if not p.empty:
        edited=st.data_editor(p,use_container_width=True,hide_index=True,num_rows="dynamic",column_config={"planned":st.column_config.NumberColumn("Planned",min_value=0,step=1)})
        if st.button("Save plan",type="primary"):
            st.session_state.plans=edited.to_dict("records"); st.success("Assurance plan saved.")
    else: st.info("No plan rows yet.")

# ----------------------------- SUBMITTED ----------------------------------
elif page=="Submitted Audits":
    st.header("Submitted Audits")
    h=df_headers(); r=df_responses()
    if h.empty: st.info("No audits have been submitted.")
    else:
        st.dataframe(h,use_container_width=True,hide_index=True)
        st.subheader("Question-level evidence")
        st.dataframe(r,use_container_width=True,hide_index=True)
        st.caption("BAR classification is retained at question level so the dashboard and corporate action workflow can distinguish control importance from aggregate conformance.")

# ----------------------------- DATA ADMIN ---------------------------------
elif page=="Data Admin":
    st.header("Data & Integration")
    st.markdown("**Target architecture:** Streamlit audit templates → Snowflake assurance tables → KPI dashboard → corporate action-management integration.")
    st.info("This Community Cloud build defaults to session storage. Perenco IT can switch `storage.mode` to `snowflake` in Streamlit secrets after deploying inside the corporate Snowflake environment.")
    c1,c2,c3=st.columns(3)
    if c1.button("Load synthetic demonstration data"):
        load_demo(); st.success("Synthetic data loaded. Every demonstration record is labelled DEMO and should not be treated as live evidence.")
    if c2.button("Clear current session data"):
        for k in ["submissions","responses","incidents","plans"]: st.session_state[k]=[]
        st.session_state.demo_loaded=False; st.success("Current session data cleared.")
    c3.metric("Storage mode", "Snowflake" if snowflake_enabled() else "Session prototype")

    payload={"exported_at":datetime.now().isoformat(),"audits":st.session_state.submissions,"responses":st.session_state.responses,"incidents":st.session_state.incidents,"plans":st.session_state.plans}
    c1,c2,c3=st.columns(3)
    c1.download_button("Download full JSON backup",json.dumps(payload,indent=2,default=str),"perenco_assurance_backup.json","application/json",use_container_width=True)
    h=df_headers(); r=df_responses(); a=df_actions()
    c2.download_button("Download audit summary CSV",h.to_csv(index=False).encode(),"cow_audits.csv","text/csv",use_container_width=True,disabled=h.empty)
    c3.download_button("Download responses CSV",r.to_csv(index=False).encode(),"cow_responses.csv","text/csv",use_container_width=True,disabled=r.empty)
    if not r.empty and not h.empty:
        bridge=r.merge(h[[c for c in ["audit_id","date","site","team","auditor","assurance_role","reference","description"] if c in h.columns]],on="audit_id",how="left")
        st.download_button("Download HTML Dashboard Bridge CSV",bridge.to_csv(index=False).encode(),"perenco_html_dashboard_bridge.csv","text/csv")
        st.caption("This flattened file is provided specifically to bridge the Streamlit form records into the existing HTML dashboard while the Snowflake integration is being established.")

    st.subheader("Restore backup")
    up=st.file_uploader("Upload a JSON backup created by this app",type=["json"])
    if up is not None and st.button("Restore uploaded backup"):
        data=json.load(up)
        for k in ["audits","responses","incidents","plans"]:
            target="submissions" if k=="audits" else k
            st.session_state[target]=data.get(k,[])
        st.success("Backup restored into the current session.")

# ----------------------------- METHOD -------------------------------------
elif page=="Method & BAR":
    st.header("Method, BAR and KPI Rules")
    st.markdown("**BAR 1 – Critical control:** directly linked to preventing a major accident, serious harm or loss of containment.  ")
    st.markdown("**BAR 2 – Key operational control:** supports safe task execution and prevents significant incidents.  ")
    st.markdown("**BAR 3 – Supporting control:** planning, administrative or good-practice control that strengthens the framework.  ")
    st.warning("BAR indicates control importance, not finding severity. A green aggregate score does not override a BAR 1 non-compliance.")
    st.markdown("**Conformance:** Yes ÷ (Yes + No). N/A is excluded.  ")
    st.markdown("**KPI 1 / 2 thresholds:** Green = 100% or more planned audits and ≥90% conformance; Amber = 70–90% planned and/or 70–89% conformance; Red = <70% planned and/or <70% conformance.  ")
    st.markdown("**KPI 3:** target 3 leadership NUI engagements per quarter plus checklist conformance and coverage.  ")
    st.markdown("**KPI 4:** visit performance by role plus Level 4 TBT / Permit / POP conformance.  ")
    st.markdown("**KPI 5:** rolling 12-month permit-controlled incident trend; the system flags an increase and HiPo/significant injury/loss-of-containment events.  ")
    st.caption("Where the source KPI specification uses qualitative terms such as 'significant increase' without a numeric threshold, this pilot does not invent a hidden score; Perenco should confirm the final governance rule before production release.")
