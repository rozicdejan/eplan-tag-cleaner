import streamlit as st
import pandas as pd
from collections import OrderedDict

st.set_page_config(
    page_title="EPLAN Tag Cleaner",
    page_icon="🧹",
    layout="wide",
)

st.title("🧹 EPLAN Tag Cleaner (EPLAN-style format)")
st.caption(
    "Example: `SERVISNA VTI NICA ELE. OMARA =LIN1+CAB1-6F13` → "
    "Description, Line (LIN1), Cabinet (CAB1), Tag (6F13)."
)

# ==========================
# SIDEBAR – GENERAL SETTINGS
# ==========================
st.sidebar.header("⚙️ Parsing settings")

delimiter = st.sidebar.text_input(
    "Delimiter between location and tag",
    value="-",
    help="Text after the LAST occurrence of this delimiter is treated as the Tag."
)

trim_at_space = st.sidebar.checkbox(
    "Trim Tag at first space",
    value=True,
    help="If enabled, everything after the first space in the Tag is removed.",
)

uppercase = st.sidebar.checkbox(
    "Convert Tag / Line / Cabinet to UPPERCASE",
    value=False,
)

remove_duplicates = st.sidebar.checkbox(
    "Remove duplicate Tags",
    value=True,
    help="If enabled, each Tag is kept only once.",
)

sort_tags = st.sidebar.checkbox(
    "Sort by Tag alphabetically",
    value=False,
)

filter_substring = st.sidebar.text_input(
    "Filter: Tag must contain (optional)",
    value="",
    help="Case-insensitive. Leave empty to disable.",
)

min_length = st.sidebar.number_input(
    "Min Tag length",
    min_value=1,
    max_value=100,
    value=1,
)

max_length = st.sidebar.number_input(
    "Max Tag length",
    min_value=1,
    max_value=100,
    value=30,
)

st.sidebar.markdown("---")
st.sidebar.header("🧾 Output format")

include_description = st.sidebar.checkbox(
    "Include Description (text before '=')",
    value=True,
)

include_line = st.sidebar.checkbox(
    "Include Line (e.g. LIN1)",
    value=True,
)

include_cabinet = st.sidebar.checkbox(
    "Include Cabinet (e.g. CAB1)",
    value=True,
)

include_tag = st.sidebar.checkbox(
    "Include Tag (e.g. 6F13)",
    value=True,
)

st.sidebar.caption(
    "These flags control how the final output string is built "
    "(for TXT preview & download)."
)

# ==========================
# FILE UPLOAD
# ==========================
uploaded_file = st.file_uploader("📤 Upload EPLAN TXT file", type=["txt"])


def parse_line(line: str) -> dict | None:
    """
    Parse a single EPLAN-style line.

    Example:
        'SERVISNA VTI NICA ELE. OMARA =LIN1+CAB1-6F13'

    Returns dict with:
        Description, Line, Cabinet, Tag
    """

    if not line or line.strip() == "":
        return None

    raw = line.strip()

    # Split description and the rest: left = Description, right = 'LIN1+CAB1-6F13'
    if "=" in raw:
        left, right = raw.split("=", 1)
        description = left.strip()
        right_part = right.strip()
    else:
        description = ""
        right_part = raw

    # Extract Tag using the delimiter (default '-')
    if delimiter not in right_part:
        # Nothing to split → no valid Tag, skip
        return None

    location_part, tag_raw = right_part.rsplit(delimiter, 1)

    # Clean Tag
    if trim_at_space:
        tag_raw = tag_raw.split()[0]

    tag = tag_raw.strip()
    if not tag:
        return None

    # Parse location (e.g. 'LIN1+CAB1')
    location_part = location_part.strip()
    line_id = ""
    cabinet_id = ""
    other_loc = []

    if location_part:
        for token in location_part.split("+"):
            token = token.strip()
            if not token:
                continue
            upper_tok = token.upper()
            if upper_tok.startswith("LIN"):
                line_id = token
            elif upper_tok.startswith("CAB"):
                cabinet_id = token
            else:
                other_loc.append(token)

    if uppercase:
        description_out = description  # usually keep text as-is
        line_id = line_id.upper() if line_id else ""
        cabinet_id = cabinet_id.upper() if cabinet_id else ""
        tag = tag.upper()
    else:
        description_out = description

    return {
        "Description": description_out,
        "Line": line_id,
        "Cabinet": cabinet_id,
        "Tag": tag,
        "OtherLocation": "+".join(other_loc) if other_loc else "",
    }


def format_output_row(row: dict) -> str:
    """
    Build the final output string for TXT/preview based on flags.
    Tries to mimic EPLAN style:

    - Description =Line+Cabinet-Tag
    - Or just Tag / Line-Tag / Line+Cabinet-Tag etc.
    """
    parts = []

    desc = row.get("Description", "")
    line_id = row.get("Line", "")
    cab_id = row.get("Cabinet", "")
    tag = row.get("Tag", "")

    # Description part
    if include_description and desc:
        parts.append(desc)

    # Location part (Line + Cabinet)
    loc_parts = []
    if include_line and line_id:
        loc_parts.append(line_id)
    if include_cabinet and cab_id:
        loc_parts.append(cab_id)

    loc_str = "+".join(loc_parts) if loc_parts else ""

    # Build location + tag
    loc_tag = ""
    if include_tag and tag:
        if loc_str:
            loc_tag = f"{loc_str}{delimiter}{tag}"
        else:
            loc_tag = tag
    else:
        loc_tag = loc_str

    # Combine description and loc/tag
    if parts and loc_tag:
        # EPLAN-style: "Description =LOC-TAG"
        return f"{parts[0]} ={loc_tag}"
    elif parts:
        return parts[0]
    elif loc_tag:
        return loc_tag
    else:
        return ""


if uploaded_file is not None:
    raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
    lines = raw_text.splitlines()

    rows = []
    for line in lines:
        parsed = parse_line(line)
        if not parsed:
            continue

        tag = parsed["Tag"]

        # Apply Tag length filter
        if not (min_length <= len(tag) <= max_length):
            continue

        # Apply substring filter on Tag
        if filter_substring:
            if filter_substring.lower() not in tag.lower():
                continue

        rows.append(parsed)

    # Remove duplicates (by Tag)
    if remove_duplicates:
        seen_tags = set()
        unique_rows = []
        for r in rows:
            key = r["Tag"]
            if key in seen_tags:
                continue
            seen_tags.add(key)
            unique_rows.append(r)
        rows = unique_rows

    # Sort by Tag
    if sort_tags:
        rows = sorted(rows, key=lambda r: r["Tag"])

    # Build formatted output strings
    for r in rows:
        r["Output"] = format_output_row(r)

    if rows:
        st.success(f"✅ Parsed and processed {len(rows)} line(s).")

        # DataFrame for display/export
        df = pd.DataFrame(rows, columns=["Output", "Description", "Line", "Cabinet", "Tag", "OtherLocation"])
        st.dataframe(df, use_container_width=True)

        # ==========================
        # DOWNLOADS
        # ==========================
        # TXT: only the formatted Output column
        txt_data = "\n".join(df["Output"].tolist())
        st.download_button(
            label="⬇️ Download formatted output as TXT",
            data=txt_data.encode("utf-8"),
            file_name="eplan_output_formatted.txt",
            mime="text/plain",
        )

        # CSV: full structured data
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Download full data as CSV",
            data=csv_data.encode("utf-8"),
            file_name="eplan_output_full.csv",
            mime="text/csv",
        )

        st.subheader("Preview (first 50 formatted lines)")
        st.text("\n".join(df["Output"].head(50).tolist()))
    else:
        st.warning("No valid lines found with current settings.")
else:
    st.info("Upload a `.txt` file to start.")
