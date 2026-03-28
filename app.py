import streamlit as st
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
import urllib.request

st.set_page_config(page_title="Green Screen Remover", layout="wide")
st.title("🎬 Green Screen Remover")
st.markdown("Remove green screen (chroma key) from **photos and videos** and replace with a custom background.")

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
}

@st.cache_data(show_spinner=False)
def load_url_image(url):
    with urllib.request.urlopen(url) as resp:
        img_array = np.asarray(bytearray(resp.read()), dtype=np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

def apply_chroma_key(frame, bg, h_min, h_max, s_min, v_min, blur=True):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    if blur:
        mask = cv2.GaussianBlur(mask, (7, 7), 0)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
    mask_inv = cv2.bitwise_not(mask)
    bg_resized = cv2.resize(bg, (frame.shape[1], frame.shape[0]))
    fg = cv2.bitwise_and(frame, frame, mask=mask_inv)
    bg_part = cv2.bitwise_and(bg_resized, bg_resized, mask=mask)
    return cv2.add(fg, bg_part)

st.sidebar.header("⚙️ Chroma Key Settings")
h_min = st.sidebar.slider("Hue Min", 0, 179, 35)
h_max = st.sidebar.slider("Hue Max", 0, 179, 85)
s_min = st.sidebar.slider("Saturation Min", 0, 255, 40)
v_min = st.sidebar.slider("Value Min", 0, 255, 40)
blur_mask = st.sidebar.checkbox("Smooth Mask Edges", value=True)

st.sidebar.header("🖼️ Background")
bg_source = st.sidebar.radio("Background Source", ["Free Backgrounds", "Upload My Own"])

bg_img = None

if bg_source == "Free Backgrounds":
    selected_bg = st.sidebar.selectbox("Choose a Background", list(FREE_BACKGROUNDS.keys()))
    with st.sidebar:
        st.markdown("**Preview:**")
        st.image(FREE_BACKGROUNDS[selected_bg], use_column_width=True)
    with st.spinner(f"Loading background: {selected_bg}..."):
        bg_img = load_url_image(FREE_BACKGROUNDS[selected_bg])
else:
    bg_file = st.sidebar.file_uploader("Upload Background Image", type=["jpg", "jpeg", "png"])
    if bg_file:
        bg_np = np.frombuffer(bg_file.read(), np.uint8)
        bg_img = cv2.imdecode(bg_np, cv2.IMREAD_COLOR)
        st.sidebar.image(bg_file, caption="Your Background", use_column_width=True)

mode = st.radio("Choose Mode", ["📷 Image", "🎥 Video"], horizontal=True)

if mode == "📷 Image":
    src_file = st.file_uploader("Upload Green Screen Image", type=["jpg", "jpeg", "png"])
    if src_file and bg_img is not None:
        src_np = np.frombuffer(src_file.read(), np.uint8)
        src_img = cv2.imdecode(src_np, cv2.IMREAD_COLOR)
        result = apply_chroma_key(src_img, bg_img, h_min, h_max, s_min, v_min, blur_mask)
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Original**")
            st.image(cv2.cvtColor(src_img, cv2.COLOR_BGR2RGB), use_column_width=True)
        with col2:
            st.markdown("**Result**")
            st.image(result_rgb, use_column_width=True)
        result_pil = Image.fromarray(result_rgb)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            result_pil.save(tmp.name)
            with open(tmp.name, "rb") as f:
                st.download_button("⬇️ Download Result Image", f, file_name="result.png", mime="image/png")
    elif src_file and bg_img is None:
        st.warning("⚠️ Please select or upload a background from the sidebar.")

elif mode == "🎥 Video":
    vid_file = st.file_uploader("Upload Green Screen Video", type=["mp4", "mov", "avi"])
    if vid_file and bg_img is not None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            tmp_in.write(vid_file.read())
            tmp_in_path = tmp_in.name
        out_path = tmp_in_path.replace(".mp4", "_output.mp4")
        cap = cv2.VideoCapture(tmp_in_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
        progress = st.progress(0, text="Processing video...")
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            result = apply_chroma_key(frame, bg_img, h_min, h_max, s_min, v_min, blur_mask)
            out.write(result)
            frame_count += 1
            progress.progress(min(frame_count / total_frames, 1.0), text=f"Processing frame {frame_count}/{total_frames}")
        cap.release()
        out.release()
        st.success("✅ Video processed!")
        with open(out_path, "rb") as f:
            st.download_button("⬇️ Download Result Video", f, file_name="result.mp4", mime="video/mp4")
        os.unlink(tmp_in_path)
        os.unlink(out_path)
    elif vid_file and bg_img is None:
        st.warning("⚠️ Please select or upload a background from the sidebar.")
