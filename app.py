import streamlit as st
import pandas as pd
import time
import re
from openai import OpenAI

# --- 1. ตั้งค่าหน้าเพจและ UI เบื้องต้น ---
st.set_page_config(page_title="FAQ Keyword Extractor", page_icon="💊", layout="wide")
st.title("💊 ระบบสกัดคีย์เวิร์ดและจัดหมวดหมู่ FAQ อัตโนมัติ")
st.markdown("ขับเคลื่อนโดย **Typhoon 2.5 API**")

# --- 2. แถบตั้งค่าด้านข้าง (Sidebar) ---
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    # --- ดึง API Key จากตู้เซฟของ Streamlit ---
try:
    api_key = st.secrets["TYPHOON_API_KEY"]
except KeyError:
    st.error("🚨 ไม่พบ API Key! กรุณาตั้งค่าในไฟล์ .streamlit/secrets.toml หรือในหน้า Settings ของ Streamlit Cloud")
    st.stop() # สั่งหยุดการทำงานทันทีเพื่อป้องกัน Error เด้งรัวๆ
    st.markdown("*(ขอ API Key ได้ฟรีที่เว็บไซต์ OpenTyphoon)*")
    
    st.divider()
    st.markdown("### 📋 หมวดหมู่ที่รองรับ")
    category_list = [
        "การขึ้นทะเบียนและอนุญาต", "การนำเข้าและส่งออก", "สถานที่ผลิตและนำเข้า", 
        "การโฆษณาผลิตภัณฑ์", "ระบบงานและ Track and Trace", "ข้อร้องเรียนและแจ้งปัญหา", "อื่นๆ"
    ]
    for cat in category_list:
        st.write(f"- {cat}")

# --- 3. สมองกล AI (ฟังก์ชันหลัก) ---
def process_faq(question, answer, api_key):
    if pd.isna(question) and pd.isna(answer):
        return "ไม่ระบุ", [None] * 7
        
    prompt = f"""อ่านข้อความคำถามและคำตอบ FAQ ด้านล่าง แล้วทำหน้าที่ 2 อย่างคือ:
1. จัดหมวดหมู่: เลือก 1 หมวดหมู่ที่ตรงที่สุดจากรายการนี้เท่านั้น {category_list}
2. สกัดคำสำคัญ: ดึงคำนามหรือศัพท์เทคนิคทางเภสัชกรรมที่สำคัญที่สุด ไม่เกิน 7 คำ (คั่นด้วยเครื่องหมายจุลภาค)

ข้อความ FAQ:
คำถาม: {question}
คำตอบ: {answer}

บังคับรูปแบบการตอบ (ห้ามมีคำอธิบายหรือคำเกริ่นนำใดๆ ตอบตามรูปแบบด้านล่างนี้เท่านั้น):
หมวดหมู่: [ชื่อหมวดหมู่ที่เลือก]
คำสำคัญ: [คำที่ 1], [คำที่ 2], [คำที่ 3]"""

    try:
        # เชื่อมต่อ API ของ Typhoon โดยใช้ OpenAI Client
        client = OpenAI(api_key=api_key, base_url="https://api.opentyphoon.ai/v1")
        response = client.chat.completions.create(
            model="typhoon-v1.5x-70b-instruct", # หรือใส่ชื่อรุ่น API ล่าสุดของ Typhoon
            messages=[
                {"role": "system", "content": "คุณคือผู้เชี่ยวชาญด้านการจัดหมวดหมู่ข้อมูลและสกัดคำศัพท์เฉพาะทาง"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        ai_output = response.choices[0].message.content
        category_result = "ไม่ระบุ"
        keywords_result = [None] * 7
        
        for line in ai_output.split('\n'):
            line = line.strip()
            if line.startswith("หมวดหมู่:"):
                cat = line.replace("หมวดหมู่:", "").strip()
                if any(c in cat for c in category_list): category_result = cat
            elif line.startswith("คำสำคัญ:"):
                raw_kws = line.replace("คำสำคัญ:", "").strip()
                words = [re.sub(r'[^\w\sก-๙]', '', w.strip()) for w in raw_kws.split(',') if w.strip()]
                while len(words) < 7: words.append(None)
                keywords_result = words[:7]
                
        return category_result, keywords_result
    except Exception as e:
        return f"Error: {str(e)}", [None] * 7

# --- 4. แบ่งหน้าจอการทำงานเป็น 2 แท็บ ---
tab1, tab2 = st.tabs(["📝 โหมดทดสอบทีละข้อ (Single Check)", "📂 โหมดจัดการไฟล์ (Batch Processing)"])

# ====== TAB 1: กรอกมือทีละข้อ ======
with tab1:
    st.header("ทดสอบสกัดคีย์เวิร์ดทีละรายการ")
    q_input = st.text_area("ป้อนคำถาม (Question):", height=100)
    a_input = st.text_area("ป้อนคำตอบ (Answer):", height=150)
    
    if st.button("🚀 ประมวลผล", type="primary", key="single_btn"):
        if not api_key:
            st.warning("⚠️ กรุณาใส่ API Key ที่เมนูด้านซ้ายก่อนค่ะ")
        elif not q_input and not a_input:
            st.warning("⚠️ กรุณากรอกข้อมูลคำถามหรือคำตอบ")
        else:
            with st.spinner("กำลังให้ AI วิเคราะห์ข้อมูล..."):
                cat, kws = process_faq(q_input, a_input, api_key)
                st.success("ประมวลผลสำเร็จ!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="หมวดหมู่ที่จัดได้", value=cat)
                with col2:
                    st.write("**คำสำคัญที่สกัดได้:**")
                    # โชว์เฉพาะคำที่ไม่ใช่ None
                    clean_kws = [k for k in kws if k is not None]
                    st.write(", ".join(clean_kws) if clean_kws else "ไม่พบคำสำคัญ")

# ====== TAB 2: อัปโหลดไฟล์ Excel ======
with tab2:
    st.header("อัปโหลดไฟล์เพื่อประมวลผลทั้งหมด")
    st.info("💡 ไฟล์ Excel ต้นฉบับต้องมีคอลัมน์ชื่อ 'Question' และ 'Answer'")
    
    uploaded_file = st.file_uploader("ลากไฟล์ Excel (.xlsx) มาวางที่นี่", type=['xlsx'])
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.write(f"พบข้อมูลทั้งหมด **{len(df)}** รายการ")
        
        if st.button("🚀 เริ่มรันข้อมูลทั้งหมด", type="primary", key="batch_btn"):
            if not api_key:
                st.error("⚠️ กรุณาใส่ API Key ที่เมนูด้านซ้ายก่อนค่ะ")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                all_cats, all_kws = [], []
                
                # วนลูปพร้อมแสดง Progress
                for i, row in df.iterrows():
                    status_text.text(f"กำลังประมวลผลรายการที่ {i+1} / {len(df)}...")
                    
                    cat, kws = process_faq(row.get('Question', ''), row.get('Answer', ''), api_key)
                    all_cats.append(cat)
                    all_kws.append(kws)
                    
                    progress_bar.progress((i + 1) / len(df))
                    # หน่วงเวลาเล็กน้อยกัน API เตะ (Rate Limit)
                    time.sleep(0.5) 
                
                # นำข้อมูลมาประกอบร่าง
                df['Predicted_Category'] = all_cats
                kw_df = pd.DataFrame(all_kws, columns=[f"Keyword-{i+1}" for i in range(7)])
                final_df = pd.concat([df, kw_df], axis=1)
                
                status_text.text("✅ ประมวลผลเสร็จสมบูรณ์!")
                st.dataframe(final_df.head(10)) # โชว์ตัวอย่าง 10 บรรทัดแรก
                
                # สร้างปุ่มดาวน์โหลด
                csv = final_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="⬇️ ดาวน์โหลดไฟล์ผลลัพธ์ (CSV)",
                    data=csv,
                    file_name="faq_result_typhoon.csv",
                    mime="text/csv",
                )