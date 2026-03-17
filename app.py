import streamlit as st
import pandas as pd
import time
import re
import io
import json
from openai import OpenAI

# --- CONFIGURATION ---
ST_PAGE_TITLE = "FAQ Keyword Extractor"
ST_PAGE_ICON = "💊"
MODEL_NAME = "typhoon-v2.5-30b-a3b-instruct"
TOP_K_KEYWORDS = 7

CATEGORY_LIST = [
    "การขึ้นทะเบียนผลิตภัณฑ์", "การต่ออายุ", "การอนุญาต", 
    "การนำเข้า", "การส่งออก", "สถานที่ผลิต", "สถานที่นำเข้า", 
    "การโฆษณาผลิตภัณฑ์", "ข้อร้องเรียนและแจ้งปัญหา", "อื่นๆ"
]

# --- INITIALIZATION ---
st.set_page_config(page_title=ST_PAGE_TITLE, page_icon=ST_PAGE_ICON, layout="wide")

@st.cache_resource
def get_ai_client():
    """สร้างและจำค่า OpenAI Client เพื่อไม่ต้องสร้างใหม่ทุกครั้ง"""
    try:
        api_key = st.secrets["TYPHOON_API_KEY"]
        return OpenAI(api_key=api_key, base_url="https://api.opentyphoon.ai/v1")
    except KeyError:
        st.error("🚨 ไม่พบ API Key! กรุณาตั้งค่าในแถบ Secrets บน Streamlit Cloud")
        st.stop()

client = get_ai_client()

# --- HELPER FUNCTIONS ---

@st.cache_data(show_spinner=False)
def process_faq(question, answer):
    """ประมวลผล FAQ ผ่าน AI พร้อมระบบ Cache เพื่อประหยัดค่า API"""
    if pd.isna(question) and pd.isna(answer):
        return "ไม่ระบุ", [None] * TOP_K_KEYWORDS
        
    prompt = f"""หน้าที่: จัดหมวดหมู่และสกัดคำสำคัญจาก FAQ
หมวดหมู่ที่เลือกได้: {CATEGORY_LIST}
เงื่อนไข: สกัดคำสำคัญเป็นคำนาม/ศัพท์เทคนิคเภสัชกรรม ไม่เกิน {TOP_K_KEYWORDS} คำ

FAQ:
คำถาม: {question}
คำตอบ: {answer}

ตอบในรูปแบบนี้เท่านั้น:
หมวดหมู่: [ชื่อหมวดหมู่]
คำสำคัญ: [คำที่ 1], [คำที่ 2]"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "คุณคือผู้เชี่ยวชาญด้านเภสัชกรรมที่ตอบข้อมูลในรูปแบบที่กำหนดอย่างเคร่งครัด"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.01,
            max_tokens=1000
        )
        
        output = response.choices[0].message.content
        cat_res, kw_res = "ไม่ระบุ", [None] * TOP_K_KEYWORDS
        
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith("หมวดหมู่:"):
                val = line.replace("หมวดหมู่:", "").strip()
                if val in CATEGORY_LIST: cat_res = val
            elif line.startswith("คำสำคัญ:"):
                raw_kws = line.replace("คำสำคัญ:", "").strip()
                words = [re.sub(r'[^\w\sก-๙]', '', w.strip()) for w in raw_kws.split(',') if w.strip()]
                kw_res = (words + [None] * TOP_K_KEYWORDS)[:TOP_K_KEYWORDS]
                
        return cat_res, kw_res
    except Exception as e:
        return f"Error: {str(e)}", [None] * TOP_K_KEYWORDS

def prepare_final_df(original_df, categories, keywords):
    """จัดการรวมข้อมูลและลบคอลัมน์ที่ซ้ำซ้อน"""
    res_df = original_df.copy()
    
    # ลบคอลัมน์เดิมที่อาจจะซ้ำกับผลลัพธ์ใหม่
    kw_cols = [f"Keyword-{i+1}" for i in range(TOP_K_KEYWORDS)]
    cols_to_drop = ['Predicted_Category'] + kw_cols
    res_df = res_df.drop(columns=[c for c in cols_to_drop if c in res_df.columns])
    
    # รวมข้อมูลใหม่
    res_df['Predicted_Category'] = categories
    kw_data = pd.DataFrame(keywords, columns=kw_cols, index=res_df.index)
    return pd.concat([res_df, kw_data], axis=1)

# --- UI COMPONENTS ---

st.title(f"{ST_PAGE_ICON} {ST_PAGE_TITLE}")
st.markdown("ขับเคลื่อนโดย **Typhoon 2.5 API**")

with st.sidebar:
    st.header("⚙️ สถานะระบบ")
    st.success("✅ ระบบพร้อมทำงาน")
    st.divider()
    st.markdown("### 📋 หมวดหมู่ที่รองรับ")
    for cat in CATEGORY_LIST:
        st.write(f"- {cat}")

tab1, tab2 = st.tabs(["📝 ทดสอบทีละข้อ", "📂 ประมวลผลไฟล์ Excel"])

# TAB 1: SINGLE CHECK
with tab1:
    q_input = st.text_area("คำถาม (Question):", height=100)
    a_input = st.text_area("คำตอบ (Answer):", height=150)
    
    if st.button("🚀 ประมวลผล", type="primary"):
        if q_input or a_input:
            with st.spinner("AI กำลังวิเคราะห์..."):
                cat, kws = process_faq(q_input, a_input)
                st.success("วิเคราะห์สำเร็จ!")
                c1, c2 = st.columns(2)
                c1.metric("หมวดหมู่", cat)
                c2.write("**คีย์เวิร์ด:**")
                c2.info(", ".join([k for k in kws if k]) or "ไม่พบข้อมูล")
        else:
            st.warning("⚠️ กรุณากรอกข้อมูลก่อนค่ะ")

# TAB 2: BATCH PROCESSING
with tab2:
    st.info("💡 ไฟล์ต้องมีคอลัมน์ 'Question' และ 'Answer'")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ Excel (.xlsx)", type=['xlsx'])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        st.write(f"📊 พบข้อมูล {len(df)} รายการ")
        
        # ตรวจสอบชื่อคอลัมน์
        cols = [str(c).strip() for c in df.columns]
        if 'Question' not in cols or 'Answer' not in cols:
            st.error("❌ ไม่พบคอลัมน์ 'Question' หรือ 'Answer' ในไฟล์")
        else:
            if st.button("🚀 เริ่มประมวลข้อมูลทั้งหมด", type="primary"):
                all_cats, all_kws = [], []
                p_bar = st.progress(0)
                status = st.empty()
                
                for i, row in df.iterrows():
                    status.text(f"กำลังรันรายการที่ {i+1}/{len(df)}...")
                    cat, kws = process_faq(row['Question'], row['Answer'])
                    all_cats.append(cat)
                    all_kws.append(kws)
                    p_bar.progress((i + 1) / len(df))
                    time.sleep(0.1) # ปรับลด delay ได้เพราะมี cache แล้ว
                
                final_df = prepare_final_df(df, all_cats, all_kws)
                status.text("✅ ประมวลผลเสร็จสิ้น!")
                st.dataframe(final_df.head(10))
                
                # Download
                out = io.BytesIO()
                final_df.to_excel(out, index=False, engine='openpyxl')
                st.download_button(
                    label="⬇️ ดาวน์โหลดผลลัพธ์ (Excel)",
                    data=out.getvalue(),
                    file_name="faq_extracted_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
