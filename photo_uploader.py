"""
Standalone Land Photo Uploader Application
Takes photos of land from user and saves them strictly isolated by Survey Number.
Prevents cross-survey number mismatch.
Run with: streamlit run photo_uploader.py
"""

import os
import streamlit as st
from pathlib import Path
from photo_manager import (
    sanitize_survey_no,
    get_survey_dir,
    save_survey_photo,
    list_survey_photos,
    delete_survey_photo,
    DEFAULT_PHOTO_DIR,
)

# Page Configuration
st.set_page_config(
    page_title="Land Photo Uploader — Survey Isolated",
    page_icon="📷",
    layout="wide",
)

# Custom Styling
st.markdown("""
<style>
    .header-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b4332;
        margin-bottom: 0.2rem;
    }
    .header-sub {
        font-size: 1.05rem;
        color: #2d6a4f;
        margin-bottom: 1.5rem;
    }
    .survey-badge {
        background-color: #e8f5e9;
        border: 2px solid #40916c;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 15px;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1b4332;
    }
    .photo-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #d8f3dc;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-title">📷 Land Photo Uploader</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="header-sub">Safely upload and organize land photos mapped strictly to specific Survey Numbers with zero cross-survey mismatch.</div>',
    unsafe_allow_html=True
)

# Sidebar: Browse Existing Surveys
with st.sidebar:
    st.header("🗂️ Survey Directory")
    st.caption("All survey plots with stored photos:")

    existing_surveys = []
    # Use /tmp on serverless/Vercel environments where root is read-only
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        DEFAULT_PHOTO_DIR = Path("/tmp") / "uploads" / "land_photos"
    else:
        DEFAULT_PHOTO_DIR = Path(__file__).resolve().parent / "uploads" / "land_photos"

    try:
        DEFAULT_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
 
    if existing_surveys:
        for s_label, count in existing_surveys:
            st.markdown(f"• **Survey `{s_label}`** — {count} photo(s)")
    else:
        st.info("No survey photos uploaded yet.")

# Main Form: Survey Number Identification
survey_no = st.text_input(
    "🏷️ Enter Survey Number (e.g. 104/A, 112, 45/paiki 1)",
    value=st.session_state.get("active_survey_no", ""),
    placeholder="Enter Survey No...",
    help="Every photo uploaded will be permanently locked and saved under this survey number.",
)

clean_survey = sanitize_survey_no(survey_no) if survey_no.strip() else None

if not clean_survey or clean_survey == "unspecified_survey":
    st.warning("⚠️ Please enter a **Survey Number** above to activate the photo uploader.")
    st.info("This prevents photos from being orphaned or mixed up with other land plots.")
else:
    # Display Active Survey Badge
    survey_dir = get_survey_dir(survey_no)
    st.markdown(
        f'<div class="survey-badge">🎯 Active Target: <strong>Survey {survey_no}</strong> &nbsp; '
        f'<span style="font-size:0.85rem; color:#555;">[Storage: <code>survey_{clean_survey}/</code>]</span></div>',
        unsafe_allow_html=True
    )

    # Upload Section
    uploaded_files = st.file_uploader(
        f"Select photos for Survey {survey_no}",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        accept_multiple_files=True,
        key=f"uploader_{clean_survey}",
    )

    if uploaded_files:
        if st.button(f"💾 Save {len(uploaded_files)} Photo(s) to Survey {survey_no}", type="primary"):
            saved_count = 0
            for f in uploaded_files:
                save_survey_photo(
                    survey_no=survey_no,
                    file_bytes=f.getvalue(),
                    original_filename=f.name,
                )
                saved_count += 1
            st.success(f"✅ Successfully saved {saved_count} photo(s) strictly under Survey **{survey_no}**!")
            st.rerun()

    # Survey Photo Gallery
    st.markdown("---")
    current_photos = list_survey_photos(survey_no)
    st.subheader(f"🖼️ Photo Gallery for Survey: {survey_no} ({len(current_photos)} photos)")

    if not current_photos:
        st.write(f"_No photos currently attached to Survey {survey_no}._")
    else:
        # Display in a 3-column responsive grid
        cols = st.columns(3)
        for idx, photo in enumerate(current_photos):
            with cols[idx % 3]:
                st.markdown('<div class="photo-card">', unsafe_allow_html=True)
                st.image(photo["file_path"], use_container_width=True)
                st.caption(f"📄 **{photo['filename']}**")
                st.caption(f"🕒 {photo['modified_at']} | 💾 {photo['size_bytes'] / 1024:.1f} KB")

                # Action buttons (Download & Delete)
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    with open(photo["file_path"], "rb") as img_file:
                        st.download_button(
                            label="⬇️ Download",
                            data=img_file.read(),
                            file_name=photo["filename"],
                            mime="image/jpeg",
                            key=f"dl_{photo['filename']}",
                            use_container_width=True,
                        )
                with b_col2:
                    if st.button("🗑️ Delete", key=f"del_{photo['filename']}", use_container_width=True):
                        delete_survey_photo(photo["file_path"], survey_no=survey_no)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
