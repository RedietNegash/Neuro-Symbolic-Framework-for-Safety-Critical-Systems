import google.generativeai as genai

# Configure with your API key
genai.configure(api_key="AIzaSyDFazWbPKjzBA6oiX6XGI7dhRiw1Rleh_c")

# Use Gemini 2.5 Flash
model = genai.GenerativeModel('models/gemini-2.5-flash')

response = model.generate_content("Hello, what can you do?")
print(response.text)