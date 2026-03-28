import streamlit as st
import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session
from io import BytesIO
import tempfile
import os
import urllib.request

st.set_page_config(page_title="AI Background Remover", layout="wide")
st.title("🤖 AI Background Remover")
st.markdown("Remove **any background** from photos and videos using AI — no green screen needed!")

FREE_BACKGROUNDS = {
    "🌆 City Skyline":      "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=1280&q=80",
    "🌲 Forest":            "https://images.unsplash.com/photo-1448375240586-882707db888b?w=1280&q=80",
    "🏖️ Beach":             "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1280&q=80",
    "🌌 Space":             "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=1280&q=80",
    "🏔️ Mountains":         "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1280&q=80",
    "🌅 Sunset":            "https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=1280&q=80",
    "🏢 Office":            "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1280&q=80",
    "🎨 Abstract Gradient": "https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=1280&q=80",
    "❄️ Snow Landscape":    "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1280&q=80",
    "🌸 Cherry Blossoms":   "https://images.unsplash.com/photo-1522383225653-ed111181a951?w=1280&q=80",
    "⬜ White":             None,
    "⬛ Black":             None,
}

@st.cache_data(show_spinner=False)
def load_url_image(url):
    with urllib.request.urlopen(url) as resp:
        img_array = np.asarray(bytearray(resp.read()), dtype=np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

@st.cache_resource
def get_session():
    return new_session("u2net")

def remove_bg_pil(pil_image, session):
    return remove(pil_image, session=session)

def composite_on_bg(fg_rgba: Image.Image, bg_bgr: np.ndarray) -> Image.Image:
    bg_rgb = cv2.cvtColor(bg_bgr, cv2.COLOR_BGR2RGB)
    bg_pil = Image.fromarray(bg_rgb).convert("RGBA")
    bg_pil = bg_pil.resize(fg_rgba.size, Image.LANCZOS)
    bg_pil.paste(fg_rgba, mask=fg_rgba.split()[3])
    return bg_pil.convert("RGB")

def pil_to_bytes(img: Image.Image, fmt="PNG") -> bytes:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

# --- Sidebar ---
st.sidebar.header("🖼️ Background")
bg_source = st.sidebar.radio("Background Source", ["Free Backgrounds", "Upload My Own", "Transparent (No Background)"])
bg_img = None

if bg_source == "Free Backgrounds":
    selected_bg = st.sidebar.selectbox("Choose a Background", list(FREE_BACKGROUNDS.keys()))
    url = FREE_BACKGROUNDS[selected_bg]
    if url:
        with st.sidebar:
            st.markdown("**Preview:**")
            st.image(url, use_column_width=True)
        with st.spinner(f"Loading: {selected_bg}..."):
            bg_img = load_url_image(url)
    else:
        color = (255, 255, 255) if "White" in selected_bg else (0, 0, 0)
        bg_img = np.full((720, 1280, 3), color, dtype=np.uint8)

elif bg_source == "Upload My Own":
    bg_file = st.sidebar.file_uploader("Upload Background Image", type=["jpg", "jpeg", "png"])
    if bg_file:
        bg_np = np.frombuffer(bg_file.read(), np.uint8)
        bg_img = cv2.imdecode(bg_np, cv2.IMREAD_COLOR)
        st.sidebar.image(bg_file, caption="Your Background", use_column_width=True)

mode = st.radio("Choose Mode", ["📷 Image", "🎥 Video"], horizontal=True)
session = get_session()

# ---- IMAGE MODE ----
if mode == "📷 Image":
    src_file = st.file_uploader("Upload Image (any background)", type=["jpg", "jpeg", "png"])
    if src_file:
        pil_img = Image.open(src_file).convert("RGB")
        with st.spinner("🤖 AI is removing background..."):
            fg_rgba = remove_bg_pil(pil_img, session)
        if bg_img is not None:
            result_pil = composite_on_bg(fg_rgba, bg_img)
            download_bytes = pil_to_bytes(result_pil, "PNG")
            result_display = result_pil
        else:
            result_display = fg_rgba
            download_bytes = pil_to_bytes(fg_rgba, "PNG")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Original**")
            st.image(pil_img, use_column_width=True)
        with col2:
            st.markdown("**Background Removed**")
            st.image(result_display, use_column_width=True)
        st.download_button("⬇️ Download Result", download_bytes, file_name="result.png", mime="image/png")

# ---- VIDEO MODE ----
elif mode == "🎥 Video":
    st.info("⚠️ AI video processing is slow. Keep videos under 30 seconds for best performance.")
    vid_file = st.file_uploader("Upload Video (any background)", type=["mp4", "mov", "avi"])
    if vid_file:
        if bg_source == "Transparent (No Background)":
            st.warning("Transparent background not supported for video. Please pick a background.")
        elif bg_img is None and bg_source == "Upload My Own":
            st.warning("⚠️ Please upload a background image from the sidebar.")
        else:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
                tmp_in.write(vid_file.read())
                tmp_in_path = tmp_in.name
            out_path = tmp_in_path.replace(".mp4", "_output.mp4")
            cap = cv2.VideoCapture(tmp_in_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
            bg_resized = cv2.resize(bg_img, (w, h))
            progress = st.progress(0, text="Processing video with AI...")
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                fg_rgba = remove_bg_pil(pil_frame, session)
                result_pil = composite_on_bg(fg_rgba, bg_resized)
                result_bgr = cv2.cvtColor(np.array(result_pil), cv2.COLOR_RGB2BGR)
                out.write(result_bgr)
                frame_count += 1
                progress.progress(min(frame_count / total_frames, 1.0),
                                   text=f"Processing frame {frame_count}/{total_frames}")
            cap.release()
            out.release()
            st.success("✅ Video processed!")
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Download Result Video", f, file_name="result.mp4", mime="video/mp4")
            os.unlink(tmp_in_path)
            os.unlink(out_path)
