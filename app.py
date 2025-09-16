import streamlit as st
from openai import OpenAI
import PyPDF2
import os
import re
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("OpenAI API key is missing. Please set it in environment variables.")
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

print("API Key Loaded ✅")

# -------- PDF TEXT EXTRACTION ----------
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = "".join([page.extract_text() or "" for page in reader.pages])
        return text
    except Exception as e:
        st.error(f"PDF Read Error: {str(e)}")
        return ""

# -------- CLEAN TEXT ----------
def clean_text(text):
    return re.sub(r'\s+', ' ', text.strip().lower())

# -------- GET RESPONSE FROM OPENAI ----------
def get_openai_response(job_description, pdf_text, prompt):
    try:
        combined_text = f"Job Description: {job_description}\nResume: {pdf_text}\nPrompt: {prompt}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # fast + cheap, can change to gpt-4o for more accuracy
            messages=[
                {"role": "system", "content": "You are an AI Resume Analyzer."},
                {"role": "user", "content": combined_text}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"

# -------- STREAMLIT UI ----------
st.set_page_config(page_title="AI Resume Analyzer", layout="centered")
st.title("\U0001F916 AI Powered Resume Screener for Accurate Hiring")

# -------- SELECT ANALYSIS TYPE ----------
option = st.selectbox("Choose what you'd like to analyze:", [
    "Resume Summary",
    "Percentage Match with Job Description",
    "Job Recommendations",
    "Skill Improvement Suggestions",
    "Rank Multiple Resumes"
])

# -------- FILE UPLOAD --------
if option == "Rank Multiple Resumes":
    uploaded_files = st.file_uploader("Upload multiple resumes (PDF format)", type=["pdf"], accept_multiple_files=True)
else:
    uploaded_file = st.file_uploader("Upload a single resume (PDF format)", type=["pdf"])
    uploaded_files = [uploaded_file] if uploaded_file else []

# -------- JOB DESCRIPTION INPUT --------
job_description = ""
if option in ["Percentage Match with Job Description", "Skill Improvement Suggestions", "Rank Multiple Resumes"]:
    job_description = st.text_area("Enter the job description")

# -------- ANALYZE BUTTON --------
if st.button("Analyze"):
    if not uploaded_files:
        st.warning("Please upload at least one resume.")
    elif option in ["Percentage Match with Job Description", "Skill Improvement Suggestions", "Rank Multiple Resumes"] and not job_description:
        st.warning("Please enter a job description.")
    else:
        resume_scores = []
        
        for uploaded_file in uploaded_files:
            raw_text = extract_text_from_pdf(uploaded_file)
            cleaned_text = clean_text(raw_text)
            filename = uploaded_file.name.replace(".pdf", "")

            if option == "Resume Summary":
                response = get_openai_response("", cleaned_text, "Provide a concise summary of the resume, highlighting key skills and experience.")
                st.subheader("Summary")
                st.write(response)

            elif option == "Percentage Match with Job Description":
                response = get_openai_response(clean_text(job_description), cleaned_text, "How well does this resume match the job description? Return only the percentage and a short explanation.")
                match = re.search(r'(\d{1,3})%', response)
                percentage = int(match.group(1)) if match else 0
                st.subheader(f"{filename} - Match Score: {percentage}%")
                st.progress(percentage / 100)
                st.write(response)

            elif option == "Job Recommendations":
                response = get_openai_response("", cleaned_text, "Based on the resume content, suggest relevant job titles or industries.")
                st.subheader("Job Recommendations")
                st.write(response)

            elif option == "Skill Improvement Suggestions":
                response = get_openai_response(clean_text(job_description), cleaned_text, "List key skills from the resume, compare with job description, and suggest additional skills to improve job alignment.")
                st.subheader("Skill Suggestions")
                st.write(response)

            elif option == "Rank Multiple Resumes":
                response = get_openai_response(clean_text(job_description), cleaned_text, "How well does this resume match the job description? Return only the percentage and a short explanation.")
                match = re.search(r'(\d{1,3})%', response)
                percentage = int(match.group(1)) if match else 0
                resume_scores.append((filename, percentage, response))

        if option == "Rank Multiple Resumes":
            resume_scores.sort(key=lambda x: x[1], reverse=True)
            df = pd.DataFrame(resume_scores, columns=["Filename", "Match Percentage", "Explanation"])
            
            st.success("✅ Ranking Complete!")
            st.subheader("📊 Ranked Resumes Table")
            st.table(df[["Filename", "Match Percentage"]])

            st.subheader("🔍 Detailed Explanations")
            for _, row in df.iterrows():
                with st.expander(f"{row['Filename']} - {row['Match Percentage']}%"):
                    st.write(row["Explanation"])
