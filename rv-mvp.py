import os
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types
from supabase import create_client

# Load Environment
load_dotenv()
client_ai = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

st.set_page_config(page_title="Resort Village AI Portal", layout="wide")
st.title("🌲 Resort Village Smart Portal (MVP Demo)")

# Load Context Bylaw
try:
    with open("bylaws.txt", "r") as f:
        bylaw_context = f.read()
except FileNotFoundError:
    bylaw_context = "Aturan Desa: Larangan membuat api unggun saat musim kering. Dermaga maksimal 5 meter."

tab1, tab2 = st.tabs(["💬 AI Bylaw Chatbot", "📸 Laporkan Masalah (AI Vision)"])

# TAB 1: BYLAW CHATBOT
with tab1:
    st.subheader("Tanya Aturan & Perda Desa")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_input := st.chat_input("Contoh: Boleh nggak bikin api unggun malam ini?"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        prompt = f"Anda adalah asisten AI resmi Resort Village. Jawab pertanyaan warga berdasarkan aturan berikut:\n{bylaw_context}\n\nPertanyaan: {user_input}"
        
        response = client_ai.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"):
            st.write(response.text)

# TAB 2: VISUAL NUISANCE REPORTER
with tab2:
    st.subheader("Lapor Fasilitas / Fasilitas Rusak via Foto")
    uploaded_file = st.file_uploader("Unggah Foto Masalah Lapangan", type=["jpg", "png", "jpeg"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Foto yang Diunggah", width=300)

        if st.button("Analisis & Kirim Laporan"):
            with st.spinner("AI sedang menganalisis foto dan membuat tiket..."):
                # Analisis Gambar dengan Gemini Multimodal
                prompt_vision = "Analisis foto ini. Berikan jawaban dengan format persis seperti ini:\nKATEGORI: [Infrastruktur/Limbah/Bahaya/Umum]\nDESKRIPSI: [Ringkasan masalah dalam 1 kalimat]\nTINDAKAN: [Rekomendasi penanganan]"
                
                res = client_ai.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[image, prompt_vision]
                )
                
                analysis_text = res.text
                st.success("Analisis AI Selesai!")
                st.info(analysis_text)

                # Simpan Foto ke Supabase Storage
                file_bytes = uploaded_file.getvalue()
                file_name = f"report_{uploaded_file.name}"
                supabase.storage.from_("village-reports").upload(file_name, file_bytes, {"content-type": uploaded_file.type})
                
                public_url = supabase.storage.from_("village-reports").get_public_url(file_name)

                # Simpan Tiket ke Supabase Database
                data = {
                    "image_url": public_url,
                    "category": "Auto-AI",
                    "description": analysis_text,
                    "status": "Pending"
                }
                supabase.table("reports").insert(data).execute()
                st.balloons()
                st.success("Laporan berhasil tersimpan di database desa!")