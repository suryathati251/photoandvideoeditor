import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import io
import tempfile
import os
from rembg import remove, new_session

st.set_page_config(page_title="BG Remover Pro", page_icon="✂️", layout="wide")
st.title("✂️ BG Remover Pro")
st.markdown("AI-powered background removal with smart image preprocessing")

st.sidebar.header("⚙️ Settings")
mode = st.sidebar.radio("Mode", ["Image", "Video"], index=0)
model_options = {
    "isnet-general-use (Best, default)": "isnet-general-use",
    "u2net_human_seg (People/Portraits)": "u2net_human_seg",
    "u2net (General)": "u2net",
    "u2netp (Fast, simple images)": "u2netp",
}
model_label = st.sidebar.selectbox("AI Model", list(model_options.keys()))
model_name = model_options[model_label]

st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Preprocessing")
auto_preprocess = st.sidebar.checkbox("Auto-Preprocess (recommended)", value=True)
with st.sidebar.expander("Manual Preprocessing Controls"):
    do_denoise   = st.checkbox("Bilateral Denoise", value=True)
    denoise_d    = st.slider("Denoise Diameter", 3, 15, 9, step=2)
    do_sharpen   = st.checkbox("Unsharp Mask Sharpen", value=True)
    sharpen_str  = st.slider("Sharpen Strength", 0.0, 3.0, 1.5, step=0.1)
    sharpen_rad  = st.slider("Sharpen Radius", 1, 5, 2)
    do_contrast  = st.checkbox("Contrast Boost", value=True)
    contrast_val = st.slider("Contrast", 0.8, 2.0, 1.1, step=0.05)
    do_upscale   = st.checkbox("Auto-Upscale Small Images", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🎭 Post-Processing")
do_cleanup   = st.sidebar.checkbox("Clean Up Mask (remove blobs)", value=True)
feather_edge = st.sidebar.slider("Feather Edge (px)", 0, 10, 2)
alpha_mat    = st.sidebar.checkbox("Alpha Matting (hair/fur edges)", value=False)
if alpha_mat:
    fg_thresh = st.sidebar.slider("FG Threshold", 220, 255, 240)
    bg_thresh = st.sidebar.slider("BG Threshold", 0, 30, 10)
    erode_sz  = st.sidebar.slider("Erode Size", 0, 40, 10)

st.sidebar.markdown("---")
st.sidebar.subheader("🖼 Background")
bg_choice = st.sidebar.selectbox("Background", [
    "Transparent (PNG)", "White", "Black", "Gray", "Light Blue", "Pastel Pink",
    "Night City", "Ocean Waves", "Desert Sand", "Green Field", "Stage Curtain", "Custom Color",
])
custom_color = "#ffffff"
if bg_choice == "Custom Color":
    custom_color = st.sidebar.color_picker("Pick color", "#ffffff")


def laplacian_score(img):
    gray = np.array(img.convert("L"))
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def preprocess_image(img, auto, controls):
    score = laplacian_score(img)
    is_blurry = score < 100
    if controls["do_upscale"] and min(img.size) < 512:
        scale = 512 / min(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    arr = np.array(img.convert("RGB"))
    if controls["do_denoise"] or (auto and is_blurry):
        d = controls["denoise_d"] if not auto else (15 if is_blurry else 9)
        arr = cv2.bilateralFilter(arr.astype(np.uint8), d, 75, 75)
    if controls["do_contrast"] or auto:
        val = controls["contrast_val"] if not auto else (1.2 if is_blurry else 1.1)
        pil = ImageEnhance.Contrast(Image.fromarray(arr)).enhance(val)
        arr = np.array(pil)
    if controls["do_sharpen"] or (auto and is_blurry):
        strength = controls["sharpen_str"] if not auto else (2.5 if is_blurry else 1.5)
        blurred = np.array(Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=controls["sharpen_rad"]))).astype(float)
        arr = np.clip(arr.astype(float) + strength * (arr.astype(float) - blurred), 0, 255).astype(np.uint8)
    return Image.fromarray(arr), score, is_blurry


def postprocess_mask(result, cleanup, feather):
    if result.mode != "RGBA":
        result = result.convert("RGBA")
    r, g, b, a = result.split()
    alpha = np.array(a)
    if cleanup:
        kernel = np.ones((5, 5), np.uint8)
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
    if feather > 0:
        alpha = cv2.GaussianBlur(alpha, (feather * 2 + 1, feather * 2 + 1), feather)
    return Image.merge("RGBA", (r, g, b, Image.fromarray(alpha)))


def apply_background(fg, bg_choice, custom_color="#ffffff"):
    solid = {
        "White": (255,255,255), "Black": (0,0,0), "Gray": (128,128,128),
        "Light Blue": (173,216,230), "Pastel Pink": (255,182,193),
        "Night City": (10,10,40), "Ocean Waves": (0,105,148),
        "Desert Sand": (210,180,140), "Green Field": (34,139,34), "Stage Curtain": (139,0,0),
    }
    if bg_choice == "Transparent (PNG)":
        return fg
    if bg_choice == "Custom Color":
        c = tuple(int(custom_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        bg = Image.new("RGBA", fg.size, c + (255,))
    else:
        bg = Image.new("RGBA", fg.size, solid[bg_choice] + (255,))
    bg.paste(fg, mask=fg.split()[3])
    return bg.convert("RGB")


def pil_to_bytes(img, fmt="PNG"):
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


controls = {
    "do_denoise": do_denoise, "denoise_d": denoise_d,
    "do_sharpen": do_sharpen, "sharpen_str": sharpen_str, "sharpen_rad": sharpen_rad,
    "do_contrast": do_contrast, "contrast_val": contrast_val, "do_upscale": do_upscale,
}

if mode == "Image":
    uploaded = st.file_uploader("Upload image", type=["jpg","jpeg","png","webp","bmp"])
    if uploaded:
        original = Image.open(uploaded).convert("RGBA")
        preprocessed, blur_score, is_blurry = preprocess_image(original.convert("RGB"), auto_preprocess, controls)
        badge = "🟡 Blurry" if is_blurry else "🟢 Sharp"
        st.info(f"Blur Score: **{blur_score:.1f}** — {badge}" + (" (enhanced preprocessing applied)" if is_blurry and auto_preprocess else ""))
        session = new_session(model_name)
        kwargs = {}
        if alpha_mat:
            kwargs = dict(alpha_matting=True, alpha_matting_foreground_threshold=fg_thresh,
                          alpha_matting_background_threshold=bg_thresh, alpha_matting_erode_size=erode_sz)
        with st.spinner("Removing background…"):
            removed = remove(preprocessed, session=session, **kwargs)
        removed = postprocess_mask(removed, do_cleanup, feather_edge)
        composited = apply_background(removed, bg_choice, custom_color)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Original**")
            st.image(original, use_container_width=True)
        with col2:
            st.markdown("**After Preprocessing**")
            st.image(preprocessed, use_container_width=True)
        with col3:
            st.markdown("**Final Result**")
            st.image(composited if bg_choice != "Transparent (PNG)" else removed, use_container_width=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("⬇ Download Result",
                               pil_to_bytes(composited if bg_choice != "Transparent (PNG)" else removed),
                               file_name="result.png", mime="image/png")
        with dl2:
            st.download_button("⬇ Download Transparent PNG", pil_to_bytes(removed),
                               file_name="transparent.png", mime="image/png")

else:
    uploaded_vid = st.file_uploader("Upload video", type=["mp4","mov","avi","mkv"])
    if uploaded_vid:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(uploaded_vid.read())
            tmp_path = tmp.name
        cap = cv2.VideoCapture(tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        st.info(f"Video: {w}×{h} @ {fps:.1f}fps — {total} frames")
        bg_colors = {
            "White":(255,255,255),"Black":(0,0,0),"Gray":(128,128,128),
            "Light Blue":(173,216,230),"Pastel Pink":(255,182,193),
            "Night City":(10,10,40),"Ocean Waves":(0,105,148),
            "Desert Sand":(210,180,140),"Green Field":(34,139,34),"Stage Curtain":(139,0,0),
        }
        if st.button("▶ Process Video"):
            out_path = tmp_path.replace(".mp4","_out.mp4")
            writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            session = new_session(model_name)
            vc = {**controls, "do_upscale": False}
            bar = st.progress(0)
            cap = cv2.VideoCapture(tmp_path)
            i = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pre, _, _ = preprocess_image(pil_frame, auto_preprocess, vc)
                rem = postprocess_mask(remove(pre, session=session), do_cleanup, feather_edge)
                if bg_choice in bg_colors:
                    bg_img = Image.new("RGBA", rem.size, bg_colors[bg_choice]+(255,))
                    bg_img.paste(rem, mask=rem.split()[3])
                    result = np.array(bg_img.convert("RGB"))
                else:
                    result = np.array(rem.convert("RGB"))
                writer.write(cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
                i += 1
                bar.progress(min(i/total, 1.0))
            cap.release()
            writer.release()
            with open(out_path, "rb") as f:
                st.download_button("⬇ Download Processed Video", f.read(), "result.mp4", "video/mp4")
            st.success("Done!")
        os.unlink(tmp_path)
