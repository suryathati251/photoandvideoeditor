# 🎬 Green Screen Remover App

A Streamlit web app to remove green screen (chroma key) from images and videos
and replace with a custom background.

## Features
- ✅ 10 free built-in backgrounds (city, beach, forest, space & more)
- ✅ Upload your own custom background
- ✅ Works with images (JPG, PNG)
- ✅ Works with videos (MP4, MOV, AVI)
- ✅ Adjustable HSV tuning sliders for precise green isolation
- ✅ Smooth mask edge option to reduce fringing
- ✅ Side-by-side original vs result preview
- ✅ One-click download of results

## Project Structure

green-screen-remover/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore

## Run Locally

git clone https://github.com/YOUR_USERNAME/green-screen-remover.git
cd green-screen-remover
pip install -r requirements.txt
streamlit run app.py

## Deploy on Streamlit Cloud

1. Push this repo to GitHub (must be public)
2. Go to https://share.streamlit.io
3. Sign in with your GitHub account
4. Click "New app"
5. Select this repo → branch: main → main file: app.py
6. Click Deploy

Your app will be live at:
https://YOUR_USERNAME-green-screen-remover-app-XXXX.streamlit.app

## Tuning Tips
- Adjust Hue Min/Max sliders if your green shade is not standard
- Enable Smooth Mask Edges for cleaner subject borders
- For best results, use well-lit footage with a solid green background
- Keep video files under 50MB for best performance on the free tier

## Dependencies
- streamlit
- opencv-python-headless
- numpy
- Pillow
