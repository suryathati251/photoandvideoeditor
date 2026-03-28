# 🤖 AI Background Remover App

Removes any background from photos and videos using AI (rembg U2-Net).

## Features
- ✅ Removes any background using AI (not just green screen)
- ✅ 10 free built-in backgrounds + white/black solid colors
- ✅ Upload your own custom background
- ✅ Transparent background export (images only)
- ✅ Works with images (JPG, PNG) and videos (MP4, MOV, AVI)

## Run Locally
pip install -r requirements.txt
streamlit run app.py

## Deploy
Push to GitHub → share.streamlit.io → select app.py → Deploy
Note: First run downloads the U2-Net model (~170MB), cached automatically.
