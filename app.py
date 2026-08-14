"""
LIFELINE — Phase 1 entry point.

Renders the public landing/login experience before authentication, and the
authenticated app (via st.navigation) afterward. Business logic lives in
services/; this file only wires up page structure and session state.
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from config.settings import (
    APP_NAME,
    APP_SUBTITLE,
    APP_TAGLINE,
    DEMO_ACCOUNT_FACILITY_BY_EMAIL,
    DEMO_ACCOUNTS,
    DEMO_MODE_LABEL,
)
from components import icons
from components.media import image_data_uri
from config.theme import inject_theme_vars
from database import seed
from database.connection import get_session, init_db
from services import auth_service

st.set_page_config(
    page_title=f"{APP_NAME} — Kisumu County",
    page_icon=":material/health_and_safety:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    css_path = Path(__file__).parent / "assets" / "styles.css"
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


@st.cache_resource
def ensure_seeded() -> bool:
    init_db()
    with get_session() as session:
        seed.run(session)
    return True


load_css()
inject_theme_vars()
ensure_seeded()

if "view" not in st.session_state:
    st.session_state["view"] = "landing"


# --------------------------------------------------------------------------
# Landing page
# --------------------------------------------------------------------------

def _collapse_html(html: str) -> str:
    """Collapse a (possibly indented, multi-line) HTML fragment to one line.

    st.markdown() runs its body through textwrap.dedent() before handing it
    to the frontend Markdown renderer. dedent() only strips whitespace that
    is common to EVERY line — so a single self-contained multi-line f-string
    (one card, uniformly indented, as in components/cards.py) dedents
    cleanly. But once several such fragments get concatenated under an
    unindented outer wrapper tag (as the journey/feature-grid sections below
    do, to keep the cards as literal DOM siblings for CSS grid/flex to
    work), the wrapper's zero indentation drops the common-prefix to zero,
    so dedent strips nothing — and any inner line still indented >=4 spaces
    then gets parsed as a literal Markdown code block instead of raw HTML
    (this is exactly the bug reported: HTML source showing up as visible
    text). Routing every fragment through this function before concatenation
    sidesteps the whole class of bug, regardless of how pieces are combined.
    """
    return re.sub(r"\s+", " ", html).strip()


def _go_login() -> None:
    st.session_state["view"] = "login"


def _go_landing() -> None:
    st.session_state["view"] = "landing"


def render_header() -> None:
    left, mid, right = st.columns([2, 4, 2])
    with left:
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:8px;font-size:1.4rem;font-weight:800;color:var(--text-primary);">
                {icons.brand(26)} {APP_NAME}</div>
            <div style="font-size:0.72rem;color:var(--text-secondary);">{APP_TAGLINE}</div>""",
            unsafe_allow_html=True,
        )
    with mid:
        st.markdown(
            """
            <div style="display:flex;gap:22px;justify-content:center;align-items:center;height:100%;
                        font-size:0.92rem;font-weight:600;color:var(--text-secondary);">
                <a href="#home" style="color:var(--text-secondary);text-decoration:none;">Home</a>
                <a href="#features" style="color:var(--text-secondary);text-decoration:none;">Features</a>
                <a href="#how-it-works" style="color:var(--text-secondary);text-decoration:none;">How It Works</a>
                <a href="#hospitals" style="color:var(--text-secondary);text-decoration:none;">Hospitals</a>
                <a href="#pricing" style="color:var(--text-secondary);text-decoration:none;">Pricing</a>
                <a href="#about" style="color:var(--text-secondary);text-decoration:none;">About</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        c1, c2 = st.columns(2)
        with c1:
            st.button("Login", width='stretch', icon=":material/login:", on_click=_go_login, key="nav_login")
        with c2:
            st.button("Start Demo", width='stretch', type="primary", icon=":material/play_circle:", on_click=_go_login, key="nav_start_demo")


def _journey_card(
    image_filename: str, object_position: str, alt_text: str,
    accent_token: str, eyebrow: str, title: str, description: str,
) -> str:
    html = f"""
    <div class="lifeline-journey-card" style="--journey-accent: var(--{accent_token});">
        <div class="lifeline-journey-image-wrap">
            <img src="{image_data_uri(image_filename)}" alt="{alt_text}"
                 style="object-position: {object_position};" />
        </div>
        <div class="lifeline-journey-body">
            <div class="lifeline-journey-eyebrow">
                <span class="lifeline-status-dot" style="background: var(--{accent_token}); margin-right:0;"></span>
                {eyebrow}
            </div>
            <div class="lifeline-journey-title">{title}</div>
            <div class="lifeline-journey-description">{description}</div>
        </div>
    </div>
    """
    return _collapse_html(html)


def render_journey_section() -> None:
    st.markdown('<div class="lifeline-section-title">How LIFELINE Connects Care</div>', unsafe_allow_html=True)
    st.caption("The referral journey moves from the referring facility, through ambulance transport, to the receiving hospital.")

    connector = f'<div class="lifeline-journey-connector">{icons.chevron_right(22)}</div>'

    cards_html = "".join([
        _journey_card(
            "reffering team.jpg", "50% 30%",
            "Healthcare team initiating a patient referral",
            "primary", "Stage 1", "Referring Hospital",
            "Initiate and coordinate patient referrals.",
        ),
        connector,
        _journey_card(
            "ambulance.jpg", "50% 55%",
            "Ambulance transporting a patient",
            "error", "Stage 2", "Ambulance",
            "Coordinate patient transportation and track the mission.",
        ),
        connector,
        _journey_card(
            "emergency team.jpg", "50% 15%",
            "Emergency healthcare team preparing to receive a patient",
            "secondary", "Stage 3", "Receiving Hospital",
            "Prepare the receiving team for patient arrival.",
        ),
    ])
    st.markdown(_collapse_html(f'<div class="lifeline-journey-track">{cards_html}</div>'), unsafe_allow_html=True)


def _photo_feature_card(
    image_filename: str, object_position: str, alt_text: str,
    accent_token: str, icon_svg: str, title: str, description: str,
) -> str:
    html = f"""
    <div class="lifeline-photo-card" style="--journey-accent: var(--{accent_token});">
        <img src="{image_data_uri(image_filename)}" alt="{alt_text}" style="object-position: {object_position};" />
        <div class="lifeline-photo-card-overlay"></div>
        <div class="lifeline-photo-card-content">
            <div class="lifeline-photo-card-icon">{icon_svg}</div>
            <div class="lifeline-photo-card-title">{title}</div>
            <div class="lifeline-photo-card-accent-line"></div>
            <div class="lifeline-photo-card-description">{description}</div>
        </div>
    </div>
    """
    return _collapse_html(html)


def render_photo_feature_grid() -> None:
    cards = [
        _photo_feature_card(
            "ambulance tracking.jpg", "50% 45%", "Ambulance Tracking",
            "error", icons.tracking(20), "Ambulance Tracking",
            "Monitor the fleet's status and simulated live position across Kisumu County.",
        ),
        _photo_feature_card(
            "Hospital referral management.jpg", "50% 30%", "Hospital Referral Management",
            "primary", icons.referrals(20), "Hospital Referral Management",
            "Create, route, and manage patient referrals between facilities.",
        ),
        _photo_feature_card(
            "location inteligence.jpg", "50% 40%", "Location Intelligence",
            "info", icons.map_icon(20), "Location Intelligence",
            "Estimate straight-line distance between facilities for planning purposes.",
        ),
        _photo_feature_card(
            "operational analytics.jpg", "50% 35%", "Operational Analytics",
            "secondary", icons.reports(20), "Operational Analytics",
            "Live dashboards covering referral volume, response time, and completion rate.",
        ),
        _photo_feature_card(
            "cost tracking.png", "35% 40%", "Cost Tracking",
            "warning", icons.savings(20), "Cost Tracking",
            "Estimate fuel and operating cost per trip from configurable cost assumptions.",
        ),
        _photo_feature_card(
            "clinical handover.jpg", "50% 25%", "Clinical Handover",
            "success", icons.handover(20), "Clinical Handover",
            "Capture structured vitals and notes at the point of patient handover.",
        ),
    ]
    st.markdown(_collapse_html(f'<div class="lifeline-feature-grid">{"".join(cards)}</div>'), unsafe_allow_html=True)


def render_landing() -> None:
    st.markdown(f'<div class="lifeline-demo-banner">{DEMO_MODE_LABEL}</div>', unsafe_allow_html=True)
    render_header()

    st.markdown('<div id="home"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="lifeline-hero">
            <h1>{APP_SUBTITLE}</h1>
            <div class="tagline">{APP_TAGLINE}</div>
            <div class="supporting">
                LIFELINE helps hospitals, health centres, and dispensaries across Kisumu County
                coordinate patient transfers and ambulance operations from a single, connected system —
                from referral creation through ambulance dispatch, live tracking, and clinical handover.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    hero_c1, hero_c2, hero_c3 = st.columns([3, 1, 1])
    with hero_c2:
        st.button("Explore LIFELINE", width='stretch', icon=":material/explore:", key="hero_explore")
    with hero_c3:
        st.button("Start Demo", width='stretch', type="primary", icon=":material/play_circle:", on_click=_go_login, key="hero_start_demo")

    st.markdown("<br/>", unsafe_allow_html=True)
    render_journey_section()

    st.markdown('<div id="features"></div>', unsafe_allow_html=True)
    st.markdown('<div class="lifeline-section-title">Everything you need to coordinate care</div>', unsafe_allow_html=True)
    render_photo_feature_grid()

    st.markdown('<div id="how-it-works"></div>', unsafe_allow_html=True)
    st.markdown('<div class="lifeline-section-title">How It Works</div>', unsafe_allow_html=True)
    steps = ["Create Referral", "Assign Ambulance", "Track Patient", "Complete Handover"]
    cols = st.columns(4)
    for i, (col, step) in enumerate(zip(cols, steps), start=1):
        with col:
            st.markdown(
                f"""<div class="lifeline-workflow-step">
                        <div class="step-number">{i}</div>
                        <div class="step-title">{step}</div>
                    </div>""",
                unsafe_allow_html=True,
            )

    st.markdown('<div id="hospitals"></div>', unsafe_allow_html=True)
    st.markdown('<div class="lifeline-section-title">Prototype Demo Network</div>', unsafe_allow_html=True)
    st.caption("The figures below describe this Phase 1 prototype's demo dataset, not a live deployed network.")
    cov_cols = st.columns(3)
    stats = [("35+", "Healthcare Facilities (demo)"), ("20+", "Ambulances (demo)"), ("Kisumu County", "Coverage Area (demo)")]
    for col, (value, label) in zip(cov_cols, stats):
        with col:
            st.markdown(
                f"""<div class="lifeline-coverage-stat">
                        <div class="stat-value">{value}</div>
                        <div class="stat-label">{label}</div>
                    </div>""",
                unsafe_allow_html=True,
            )

    st.markdown('<div id="pricing"></div>', unsafe_allow_html=True)
    st.markdown('<div class="lifeline-section-title">Pricing</div>', unsafe_allow_html=True)
    st.markdown(
        """<div class="lifeline-panel" style="text-align:center;">
        This Phase 1 prototype is a non-commercial demonstration build.
        Pricing and deployment plans for hospitals and county health departments
        will be defined in a later phase, once real integrations are scoped.
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div id="about"></div>', unsafe_allow_html=True)
    st.markdown('<div class="lifeline-section-title">About This Prototype</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="lifeline-panel">
        {APP_NAME} Phase 1 is a working prototype of a hospital referral and ambulance
        coordination platform for Kisumu County. All facility coordinates, ambulance
        positions, and patient/driver records in this build are demo/seed data.
        Ambulance movement is simulated (straight-line interpolation), not real GPS.
        See the README for what is deferred to later phases.
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    cta_l, cta_mid, cta_r = st.columns([2, 1, 2])
    with cta_mid:
        st.button("Start Demo", type="primary", width='stretch', icon=":material/play_circle:", on_click=_go_login, key="footer_start_demo")


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------

def render_login() -> None:
    st.markdown(f'<div class="lifeline-demo-banner">{DEMO_MODE_LABEL}</div>', unsafe_allow_html=True)
    st.button("Back to Home", icon=":material/arrow_back:", on_click=_go_landing, key="back_to_home")

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            f"""<div style="text-align:center;margin-bottom:1rem;">
                    <div style="display:flex;align-items:center;justify-content:center;gap:8px;
                                font-size:1.7rem;font-weight:800;color:var(--text-primary);">
                        {icons.brand(28)} {APP_NAME}</div>
                    <div style="color:var(--text-secondary);">Sign in to the demo environment</div>
                </div>""",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            role_labels = {a["role"]: a["role"].title() for a in DEMO_ACCOUNTS}
            selected_role = st.selectbox("Role", options=list(role_labels.keys()), format_func=lambda r: role_labels[r])
            matching_account = next(a for a in DEMO_ACCOUNTS if a["role"] == selected_role)

            prefill = st.checkbox(f"Use demo {matching_account['role'].title()} credentials", value=True)
            default_email = matching_account["email"] if prefill else ""
            default_password = matching_account["password"] if prefill else ""

            with st.form("login_form"):
                email = st.text_input("Email / Username", value=default_email, placeholder="you@demo.lifeline")
                password = st.text_input("Password", value=default_password, type="password")
                submitted = st.form_submit_button("Sign In", type="primary", icon=":material/login:", width='stretch')

            if submitted:
                with get_session() as session:
                    success = auth_service.login(session, email, password)
                if success:
                    st.session_state["view"] = "landing"
                    st.rerun()
                else:
                    st.error("Invalid email or password. Try one of the demo accounts below.")

        st.markdown("<br/>", unsafe_allow_html=True)
        with st.expander("Demo account credentials", expanded=False):
            for account in DEMO_ACCOUNTS:
                st.markdown(
                    f"**{account['role'].title()}** — `{account['email']}` / `{account['password']}`"
                )
            st.caption(
                "These are non-production demo accounts using a simplified password scheme. "
                "Production authentication (Argon2id/OIDC) is a later phase."
            )


# --------------------------------------------------------------------------
# Authenticated app
# --------------------------------------------------------------------------

def render_authenticated() -> None:
    import pages.ambulances as ambulances_page
    import pages.dashboard as dashboard_page
    import pages.handover as handover_page
    import pages.reports as reports_page
    import pages.referrals as referrals_page
    import pages.tracking as tracking_page

    user = auth_service.current_user()

    with st.sidebar:
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:8px;font-size:1.3rem;font-weight:800;
                        color:var(--text-primary);margin-bottom:0.5rem;">
                {icons.brand(24)} {APP_NAME}</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="lifeline-demo-banner">{DEMO_MODE_LABEL}</div>', unsafe_allow_html=True)
        facility = DEMO_ACCOUNT_FACILITY_BY_EMAIL.get(user["email"], "Kisumu County Network")
        st.markdown(
            f"""<div class="lifeline-user-card">
                    <div class="name">{user['full_name']}</div>
                    <div class="role">{user['role'].title()} · {facility}</div>
                </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Logout", width='stretch', icon=":material/logout:"):
            auth_service.logout()

    pages = [
        st.Page(dashboard_page.render, title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
        st.Page(referrals_page.render, title="Referrals", icon=":material/assignment:", url_path="referrals"),
        st.Page(ambulances_page.render, title="Ambulance Fleet", icon=":material/emergency:", url_path="ambulances"),
        st.Page(tracking_page.render, title="Live Tracking", icon=":material/location_on:", url_path="tracking"),
        st.Page(handover_page.render, title="Patient Handover", icon=":material/assignment_turned_in:", url_path="handover"),
        st.Page(reports_page.render, title="Reports", icon=":material/bar_chart:", url_path="reports"),
    ]
    # Exposed so pages can call st.switch_page(...) on each other (e.g. a
    # dashboard KPI card jumping to a pre-filtered Referrals/Fleet view).
    # st.switch_page requires the actual Page object for callable-based
    # pages, which is only constructed here, so it's handed off via
    # session_state rather than pages importing this module (would be
    # circular: app.py already imports pages.*).
    st.session_state["_nav_pages"] = {p.url_path: p for p in pages}

    navigation = st.navigation(pages)
    navigation.run()


# --------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------

if not auth_service.is_authenticated():
    if st.session_state["view"] == "login":
        render_login()
    else:
        render_landing()
else:
    render_authenticated()
