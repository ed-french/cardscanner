import os
from flask import Flask, request, render_template_string, send_file
from google import genai
from google.genai import types
from PIL import Image
import io
import datetime
import credentials

app = Flask(__name__)
client = genai.Client(api_key=credentials.gemini_api_key)

# Simple HTML UI
HTML_TEMPLATE = '''
<!doctype html>
<title>Business Card Scanner</title>
<h1>Upload Business Card</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file accept="image/*" capture="camera">
  <input type=submit value=Upload>
</form>
'''


def clean_vcard_for_windows(raw_text):
    # 1. Remove any AI markdown or whitespace
    text = raw_text.strip().replace('```', '').replace('vcard', '').strip()
    
    # 2. Split into lines and strip each line of trailing/leading spaces
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # 3. Force CRLF and a blank line at the end
    clean_vcard = "\r\n".join(lines) + "\r\n\r\n"
    
    return clean_vcard

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            # Convert image for Gemini
            img = Image.open(file.stream)
            
            # Prompt Gemini to be a vCard generator
            prompt = """
Extract contact info from this card. 
Return ONLY a vCard 2.1 string. 
- Use VERSION:2.1
- Layout must be:
  1. BEGIN:VCARD
  2. VERSION:2.1
  3. N:Last;First;Middle;Prefix;Suffix (Use exactly 4 semicolons)
  4. FN:Full Name
  5. ORG:Organization
  6. TITLE:Job Title
  7. TEL;WORK;VOICE:Number
  8. ADR;WORK:;;Street;City;State;Zip;Country (Use exactly 6 semicolons)
  9. EMAIL;INTERNET:Email
  10. URL:Website
  11. END:VCARD
- Do NOT use 'TYPE=' labels.
- Do NOT use the 'tel:' prefix.
"""
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=[prompt, img]
            )
            
            vcard_content = response.text.strip().replace('```', '').replace('vcard', '')


            print(vcard_content)

            content_lines=vcard_content.splitlines()

            name="dummy_name"
            for content in content_lines:
                if content.startswith("FN:"):
                    name=content.split(":")[1]


            dts=datetime.datetime.now().isoformat().replace(":","_")

            filename=f"{name} {dts}.vcf"

            print(f"Saving file: <<<{filename}>>>")


            vcard_to_save = clean_vcard_for_windows(response.text)
            with open("cards/"+filename, "w", encoding="utf-8", newline='') as f:
                f.write(vcard_to_save)



            
            # Serve the result as a downloadable file
            return send_file(
                io.BytesIO(vcard_to_save.encode()),
                mimetype='text/vcard',
                as_attachment=True,
                attachment_filename=filename
            )
    return HTML_TEMPLATE

if __name__ == '__main__':
    # host='0.0.0.0' allows connections from your phone on the same network
    app.run(host='0.0.0.0', port=80)