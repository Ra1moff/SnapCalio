import os
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def analyze_food_image(image_path):
    """
    Analyzes an image of food using Gemini 1.5 Flash.
    Returns a dictionary with nutritional information, or None if failed.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set.")
        return None
        
    try:
        # Configure the SDK
        genai.configure(api_key=api_key)
        
        # Load the image using Pillow
        img = Image.open(image_path)
        
        # We use gemini-3.5-flash which is the active model supporting multimodal inputs and structured outputs
        model = genai.GenerativeModel('gemini-3.5-flash')
        
        prompt = """
        Siz professional parhezshunos (nutritionist) va oziq-ovqat mutaxassisiz. 
        Ushbu rasmdagi yegulik/ovqatni aniqlang va uning porsiyasi (hajmi) bo'yicha quyidagi ma'lumotlarni hisoblang:
        1. Jami kaloriya miqdori (calories, kcal birlikda)
        2. Oqsil miqdori (protein, grammda)
        3. Uglevod miqdori (carbs, grammda)
        4. Yog' miqdori (fat, grammda)
        5. Ovqatning qisqacha tavsifi (o'zbek tilida, porsiyasi, tarkibiy qismlari va h.k.)

        Siz FAQAT va FAQAT quyidagi kalitlar va ko'rsatilgan formatga ega bo'lgan JSON ma'lumotni qaytarishingiz kerak:
        {
          "food_name": "Ovqat nomi o'zbek tilida (masalan: Palov, Somsa, Qovurilgan tuxum, Pizza)",
          "calories": 450,
          "protein": 18.5,
          "carbs": 55.0,
          "fat": 15.2,
          "description": "Taomning o'zbekcha qisqacha tavsifi. DIQQAT: ushbu description qiymati matnida yangi qatorga o'tish (newline, \\n) belgilarini mutlaqo ishlatmang, barchasini bitta qatorda yozing. Shuningdek matn ichida qo'shtirnoq ishlatmang, zarur bo'lsa yakka tirnoq ' ishlating."
        }
        
        Hech qanday boshqa matn, izoh yoki markdown belgilarini yozmang.
        """
        
        # Call the API with JSON enforcement
        response = model.generate_content(
            contents=[prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        
        text_response = response.text.strip()
        
        # Parse the JSON response
        try:
            data = json.loads(text_response)
        except json.JSONDecodeError:
            # Fallback: clean raw newlines in string properties
            cleaned_text = text_response.replace('\n', ' ').replace('\r', '')
            data = json.loads(cleaned_text)
        
        # Validate and format fields
        result = {
            "food_name": str(data.get("food_name", "Noma'lum taom")),
            "calories": round(float(data.get("calories", 0.0)), 1),
            "protein": round(float(data.get("protein", 0.0)), 1),
            "carbs": round(float(data.get("carbs", 0.0)), 1),
            "fat": round(float(data.get("fat", 0.0)), 1),
            "description": str(data.get("description", "Skan qilingan yegulik."))
        }
        return result
        
    except Exception as e:
        print(f"Gemini API error or JSON parsing failed: {e}")
        return None
