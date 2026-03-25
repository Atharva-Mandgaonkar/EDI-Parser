# 🏥 EDI Parser & X12 File Validator (835 / 837 / 834)

A full-stack **US Healthcare EDI Parser and Validator** that processes X12 files (837 Claims, 835 Remittance, 834 Enrollment), detects errors, and provides structured output with validation reports.

---

## 🚀 Live Demo  
🔗 **Deployed App:** https://edi-backend-peach.vercel.app/  

---

## 📌 Features

- 📂 Upload `.edi` / `.txt` files  
- 🔍 Automatically detects transaction type (837 / 835 / 834)  
- 🧩 Parses EDI into structured JSON format  
- ✅ Validates segments using predefined X12 rules  
- ⚠️ Detects errors with detailed explanations  
- 🤖 AI-based suggestions for fixing errors  
- 📊 Clean UI for viewing parsed output and validation report  

---

## 🛠️ Tech Stack

- **Frontend:** HTML, CSS, JavaScript / React  
- **Backend:** Python (Flask / FastAPI)  
- **Parsing Logic:** Custom X12 parser
- **Deployment:** Vercel and Render

---

## 📂 Sample Files (For Testing)

This repository includes **ready-to-use EDI sample files**:

| File Name | Description |
|----------|------------|
| `sample_837.edi` | Medical Claim |
| `sample_835.edi` | Payment/Remittance |
| `sample_834.edi` | Enrollment |
| `error_sample.edi` | File with intentional errors |

👉 Use these files to test parsing and validation features.

---

## ⚙️ How It Works

1. Upload an EDI file  
2. System reads ISA/GS/ST segments  
3. Identifies transaction type  
4. Parses hierarchical loops and segments  
5. Validates using X12 rules  
6. Generates:
   - Parsed JSON  
   - Error report  
   - Suggestions  
---

