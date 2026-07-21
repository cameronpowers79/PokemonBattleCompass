'''import streamlit as st


def apply_app_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: "Aptos", "Segoe UI", sans-serif;
        }

        h1, h2, h3, h4,
        .stMarkdown h1,
        .stMarkdown h2,
        .stMarkdown h3,
        .stMarkdown h4 {
            font-family: "Exo 2", "Bahnschrift", "Aptos", sans-serif;
            font-weight: 700;
            letter-spacing: 0.01em;
        }

        h1 {
            text-align: center;
        }

        .app-tagline {
            text-align: center;
            font-size: 1.1rem;
            color: rgba(255,255,255,0.72);
            margin-bottom: 0.5rem;
        }

        [data-testid="stMetricValue"] {
            font-family: "Bahnschrift", "Aptos", "Segoe UI", sans-serif;
            font-weight: 500;
        }

        [data-testid="stMetricLabel"] {
            font-family: "Aptos", "Segoe UI", sans-serif;
        }

        section[data-testid="stSidebar"] {
            width: 260px !important;
        }

        section[data-testid="stSidebar"] > div {
            width: 260px !important;
        }

        .recommendation-card {
            background: linear-gradient(180deg, #151923 0%, #10141c 100%);
            border: 1px solid rgba(79, 156, 255, 0.45);
            border-radius: 18px;
            padding: 28px 32px;
            box-shadow: 
                0 0 18px rgba(79, 156, 255, 0.18),
                0 0 4px rgba(79, 156, 255, 0.35);
        }

        .card-kicker {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 24px;
        }

        .pokemon-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 2.9rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 12px;
        }

        .type-badge-row {
            display: flex;
            gap: 8px;
            align-items: center;
            justify-content: center;
            margin-bottom: 24px;
        }

        .type-badge {
            height: 24px;
            width: auto;
        }

        .card-divider {
            height: 1px;
            background: rgba(255,255,255,0.16);
            margin: 20px 0 24px 0;
        }

        .move-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 18px;
        }
        
        .best-move-column {
            min-width: 0;
        }

        .best-move-effectiveness {
            display: inline-block;
            width: fit-content;
            max-width: 100%;
            margin: 16px 0 0 0;
            padding: 10px 14px;
        }

        .label {
            color: rgba(255,255,255,0.72);
            font-size: 0.92rem;
            margin-bottom: 6px;
        }

        .move-name,
        .ratio-value {
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 2.35rem;
            line-height: 1.1;
            font-weight: 500;
        }

        .matchup-strength {
            min-width: 230px;
        }

        .matchup-strength-title {
            color: rgba(255,255,255,0.72);
            font-size: 0.92rem;
            margin-bottom: 12px;
        }

        .matchup-meter {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 4px;
            position: relative;
            margin-bottom: 16px;
        }

        .matchup-segment {
            position: relative;
            height: 14px;
            opacity: 0.38;
            border: 1px solid rgba(255,255,255,0.12);
        }

        .matchup-segment:first-child {
            border-radius: 999px 4px 4px 999px;
        }

        .matchup-segment:last-child {
            border-radius: 4px 999px 999px 4px;
        }

        .matchup-challenging {
            background: linear-gradient(180deg, #ef4444, #b91c1c);
        }

        .matchup-competitive {
            background: linear-gradient(180deg, #fb923c, #ea580c);
        }

        .matchup-favorable {
            background: linear-gradient(180deg, #d9f044, #a3c922);
        }

        .matchup-comfortable {
            background: linear-gradient(180deg, #4ade80, #16a34a);
        }

        .matchup-immune {
            background: linear-gradient(180deg, #60a5fa, #2563eb);
        }

        .matchup-segment-active {
            opacity: 1;
            box-shadow:
                0 0 0 1px rgba(255,255,255,0.20),
                0 0 10px rgba(255,255,255,0.12);
        }

        .matchup-pointer {
            position: absolute;
            left: 50%;
            bottom: -10px;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 7px solid transparent;
            border-right: 7px solid transparent;
            border-bottom: 9px solid rgba(255,255,255,0.92);
        }

        .matchup-strength-label {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 3px;
        }

        .matchup-label-challenging {
            color: #f87171;
        }

        .matchup-label-competitive {
            color: #fb923c;
        }

        .matchup-label-favorable {
            color: #d9f044;
        }

        .matchup-label-comfortable {
            color: #4ade80;
        }

        .matchup-label-immune {
            color: #60a5fa;
        }

        .other-option-matchup-line {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin: 0.2rem 0 0.6rem 0;
        }

        .other-option-strength {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.1;
        }

        .other-option-ratio {
            color: rgba(255,255,255,0.50);
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 0.82rem;
        }

        .other-option-heading {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 0.25rem 0 0.85rem 0;
        }

        .other-option-heading .pokemon-sprite {
            transform: none;
            flex-shrink: 0;
        }

        .other-option-rank,
        .other-option-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            line-height: 1;
        }

        .other-option-rank {
            margin-right: -4px;
}

        .matchup-ratio-detail {
            color: rgba(255,255,255,0.50);
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 0.82rem;
        }

        .effectiveness-pill {
            border-radius: 12px;
            padding: 14px 18px;
            font-size: 1rem;
            font-weight: 600;
            margin: 8px 0 28px 0;
        }

        .effectiveness-good {
            background: rgba(34, 197, 94, 0.20);
            color: #4ade80;
        }

        .effectiveness-neutral {
            background: rgba(59, 130, 246, 0.18);
            color: #93c5fd;
        }

        .effectiveness-caution {
            background: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
        }

        .effectiveness-bad {
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
        }

        .section-title {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .why-box {
            background: rgba(59, 130, 246, 0.14);
            border: 1px solid rgba(59, 130, 246, 0.24);
            border-radius: 12px;
            padding: 14px 16px;
            color: #dbeafe;
            margin-bottom: 22px;
        }

        .notes-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .battle-note {
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            gap: 10px;
            align-items: flex-start;
            font-size: 0.98rem;
        }

        .note-info {
            background: rgba(59, 130, 246, 0.12);
            color: #bfdbfe;
        }

        .note-opportunity {
            background: rgba(34, 197, 94, 0.12);
            color: #bbf7d0;
        }

        .note-caution {
            background: rgba(245, 158, 11, 0.14);
            color: #fde68a;
        }

        .note-warning {
            background: rgba(239, 68, 68, 0.15);
            color: #fecaca;
        }

        .note-icon {
            min-width: 22px;
        }

        .side-card {
            background: linear-gradient(180deg, #151923 0%, #10141c 100%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 24px 28px;
            margin-bottom: 20px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.20);
        }

        .side-card-title {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 16px;
        }

        .opponent-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 10px;
        }   

        .opponent-level {
            color: rgba(255,255,255,0.72);
            font-size: 1rem;
            margin-top: 8px;
        }

        .snapshot-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
            margin-bottom: 20px;
        }

        .snapshot-value {
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 2rem;
            font-weight: 600;
        }

        .snapshot-move-label {
            color: rgba(255,255,255,0.72);
            font-size: 0.9rem;
            margin-bottom: 4px;
        }

        .snapshot-move {
            display: inline-block;
            transform: translateY(1px);
        }

        .snapshot-score-line {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .item-boost-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.12rem;
            font-weight: 700;
            color: rgba(255,255,255,0.97);
            margin-bottom: 4px;
        }

        .item-boost-details {
            position: relative;
            display: inline-block;
        }

        .item-boost-details summary {
            list-style: none;
        }

        .item-boost-details summary::-webkit-details-marker {
            display: none;
        }

        .item-boost-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;

            width: 25px;
            height: 25px;

            border: 1px solid rgba(79, 156, 255, 0.60);
            border-radius: 50%;

            color: #60a5fa;
            background: rgba(79, 156, 255, 0.14);

            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1;

            cursor: pointer;
            user-select: none;

            box-shadow:
                0 0 8px rgba(79, 156, 255, 0.18);
        }

        .item-boost-icon:hover {
            color: #93c5fd;
            background: rgba(79, 156, 255, 0.22);
        }

        .item-boost-popover {
            position: absolute;
            z-index: 20;
            top: 32px;
            left: 0;

            width: 220px;
            padding: 12px 14px;

            background: #151923;
            border: 1px solid rgba(79, 156, 255, 0.38);
            border-radius: 12px;

            color: rgba(255,255,255,0.86);
            font-size: 0.88rem;
            line-height: 1.45;

            box-shadow:
                0 10px 30px rgba(0,0,0,0.45),
                0 0 12px rgba(79, 156, 255, 0.12);
        }

        .item-boost-title {
            color: #93c5fd;
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .item-boost-divider {
            height: 1px;
            background: rgba(255,255,255,0.10);
            margin: 8px 0;
        }

        .move-name-line,
        .snapshot-move-line {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .snapshot-move-line {
            margin-bottom: 12px;
        }

        .pokemon-header-row {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            text-align: center;
        }

       .pokemon-text-block {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .sprite-placeholder {
            border: 1px dashed rgba(255,255,255,0.25);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255,255,255,0.45);
            font-size: 2rem;
            font-weight: 700;
            flex-shrink: 0;
        }

        .sprite-frame {
            width: 88px;
            height: 88px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: visible;
            flex-shrink: 0;
        }

        .pokemon-sprite {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
            transform: scale(1.35);
            transform-origin: center center;
            display: block;
        }

       /* Battle-setting selector labels */

        .battle-setting-label {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.09rem;
            font-weight: 600;
            color: rgba(255,255,255,0.94);
            margin: 0 0 0.2rem 0;
        }

        @media (max-width: 1350px) {
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column;
            }

            div[data-testid="stHorizontalBlock"] > div {
                width: 100% !important;
            }
        }

        /* My Team detail panel */

        .team-detail-card {
            background: linear-gradient(180deg, #151923 0%, #10141c 100%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 24px 28px;
            margin-top: 22px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.20);
        }

        .team-detail-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 10px;
        }

        .team-detail-header .type-badge-row {
            margin-bottom: 8px;
        }

        .team-detail-name {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
            margin: 10px 0 8px 0;
        }

        .team-detail-level {
            color: rgba(255,255,255,0.70);
            font-size: 1.25rem;
            margin-top: 4px;
        }

        .team-detail-section-title {
            font-family: "Exo 2", "Bahnschrift", sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .team-stat-list {
            display: flex;
            flex-direction: column;
            gap: 9px;
            margin-bottom: 24px;
        }

        .team-stat-row {
            display: grid;
            grid-template-columns: 44px minmax(120px, 1fr) 48px;
            align-items: center;
            gap: 10px;
        }

        .team-stat-label {
            color: rgba(255,255,255,0.72);
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
        }

        .team-stat-track {
            height: 16px;
            background: rgba(255,255,255,0.09);
            border-radius: 999px;
            overflow: hidden;
        }

        .team-stat-fill {
            height: 100%;
            min-width: 3px;
            border-radius: 999px;
        }

        .team-stat-fill-hp {
            background: linear-gradient(
                90deg,
                rgba(34, 197, 94, 0.70),
                rgba(74, 222, 128, 0.98)
            );
        }

        .team-stat-fill-atk {
            background: linear-gradient(
                90deg,
                rgba(220, 38, 38, 0.72),
                rgba(248, 113, 113, 0.98)
            );
        }

        .team-stat-fill-def {
            background: linear-gradient(
                90deg,
                rgba(217, 119, 6, 0.72),
                rgba(251, 191, 36, 0.98)
            );
        }

        .team-stat-fill-spa {
            background: linear-gradient(
                90deg,
                rgba(37, 99, 235, 0.72),
                rgba(96, 165, 250, 0.98)
            );
        }

        .team-stat-fill-spd {
            background: linear-gradient(
                90deg,
                rgba(124, 58, 237, 0.72),
                rgba(167, 139, 250, 0.98)
            );
        }

        .team-stat-fill-spe {
            background: linear-gradient(
                90deg,
                rgba(219, 39, 119, 0.72),
                rgba(244, 114, 182, 0.98)
            );
        }

        .team-stat-value {
            font-family: "Bahnschrift", "Aptos", sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            text-align: right;
       }   

        .team-move-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }

        .team-move {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;

            color: white;

            border-radius: 12px;

            padding: 10px 14px;

            font-weight: 700;

            border: 1px solid rgba(255,255,255,.18);

            box-shadow:
                inset 0 1px rgba(255,255,255,.18),
                0 2px 6px rgba(0,0,0,.18);

            text-shadow: 0 1px 2px rgba(0,0,0,.35);
        }

        .team-move-name{
            overflow:hidden;
            text-overflow:ellipsis;
            white-space:nowrap;
        }

        .team-move-badge{

            display:flex;

            align-items:center;

            flex-shrink:0;
        }

        .team-detail-footer {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .team-detail-field {
            background: rgba(255,255,255,0.04);
            border-radius: 10px;
            padding: 10px 12px;
        }

        .team-detail-field-label {
            color: rgba(255,255,255,0.62);
            font-size: 0.78rem;
            margin-bottom: 3px;
        }

        .st-key-save_team_button div[data-testid="stButton"] {
            display: flex;
            justify-content: center;
        }

        .st-key-save_team_button div[data-testid="stButton"] > button {
            width: auto;
        }

        .why-more-link {
            margin-top: 0.75rem;
            padding-top: 0.6rem;
            border-top: 1px solid rgba(255,255,255,0.08);

            color: #69A8FF;
            font-size: 0.92rem;
            font-weight: 600;

            opacity: 0.95;
        }

        /* ---------- Branding ---------- */

        .app-branding {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1.5rem auto;
        }

        .brand-logo {
            display: block;
            width: 122px;
            height: auto;
            margin: 0 auto 0.35rem auto;
        }

        .brand-wordmark {
            display: block;
            width: min(840px, 95%);
            height: auto;
            margin: 0 auto 0.75rem auto;
        }

        @media (max-width: 900px) {

            .team-move-grid,
            .team-detail-footer {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 700px) {

            .card-kicker {
                font-size: clamp(1.25rem, 5.2vw, 1.5rem);
                white-space: nowrap;
            }

            .move-row {
                display: grid;
                grid-template-columns: 1fr;
                gap: 18px;
            }

            .matchup-strength {
                width: 100%;
                min-width: 0;
            }

            .matchup-meter {
                width: 100%;
            }

            .best-move-effectiveness {
                display: block;
                width: auto;
            }
}

</style>
        """,
        unsafe_allow_html=True,
    )'''