from pyrogram import Client
import json

file = "telegram.json"

print("Enter your API ID and API HASH from https://my.telegram.org")
api_id = int(input("API ID: "))
api_hash = input("API HASH: ")

app = Client("my_app", api_id=api_id, api_hash=api_hash, in_memory=True)
with app:
    with open(file, "w") as f:
        json.dump(
            {
                "api_id": api_id,
                "api_hash": api_hash,
                "session_string": app.export_session_string(),
            },
            f,
        )
    print(f"Session string saved to {file}")
