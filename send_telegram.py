import json
import urllib.request
import urllib.parse
import ssl

# Bypass SSL verification if needed
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Read credentials
with open("secrets.json", "r") as f:
    secrets = json.load(f)

bot_token = secrets.get("TELEGRAM_BOT_TOKEN")
chat_id = secrets.get("AJAY_TELEGRAM_ID")

# Read JARVIS Blueprint
with open("JARVIS_BLUEPRINT.md", "r") as f:
    blueprint_text = f.read()

# Telegram API URL
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

# Send in chunks if it's too long (Telegram limit is 4096 chars)
max_length = 4000
chunks = [blueprint_text[i:i+max_length] for i in range(0, len(blueprint_text), max_length)]

print(f"Sending {len(chunks)} chunks to Telegram ID: {chat_id}")

for i, chunk in enumerate(chunks):
    data = {
        "chat_id": chat_id,
        "text": chunk,
        "parse_mode": "Markdown"
    }

    # encode data
    encoded_data = json.dumps(data).encode('utf-8')

    req = urllib.request.Request(url, data=encoded_data, headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, context=ctx)
        print(f"Chunk {i+1} sent successfully. Response: {response.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error sending chunk {i+1}: {e}")
        # Try without markdown parsing just in case there are unclosed tags
        try:
            print("Retrying without Markdown parsing...")
            data["parse_mode"] = ""
            encoded_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=encoded_data, headers={'Content-Type': 'application/json'})
            response = urllib.request.urlopen(req, context=ctx)
            print(f"Chunk {i+1} sent successfully on retry.")
        except Exception as retry_e:
            print(f"Retry failed: {retry_e}")
