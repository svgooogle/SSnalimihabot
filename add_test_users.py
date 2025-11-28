import json
import os

PARTICIPANTS_FILE = "participants.json"

def load_data():
    if os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"participants": {}}

def save_data(data):
    with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_test_users():
    data = load_data()
    participants = data.get("participants", {})

    test_users = [
        {
            "user_id": "10001",
            "name": "Тест_Иван",
            "username": "TestIvan",
            "wishlist": "Хочу новую клавиатуру и кружку с котиком."
        },
        {
            "user_id": "10002",
            "name": "Тест_Мария",
            "username": "TestMaria",
            "wishlist": "Хочу книгу по Python и набор для рисования."
        },
        {
            "user_id": "10003",
            "name": "Тест_Петр",
            "username": "TestPetr",
            "wishlist": "Хочу умную колонку и теплый свитер."
        },
        {
            "user_id": "10004",
            "name": "Тест_Анна",
            "username": "TestAnna",
            "wishlist": "Хочу беспроводные наушники и билет в кино."
        },
    ]

    for user in test_users:
        # Check if user already exists to avoid duplicates
        if not any(p["user_id"] == user["user_id"] for p in participants.values()):
            # Using a dummy chat_id for test users, it's not critical as long as it's unique
            dummy_chat_id = f"test_{user["user_id"]}"
            participants[dummy_chat_id] = user
    
    data["participants"] = participants
    save_data(data)
    print(f"{len(test_users)} тестовых пользователей добавлены/обновлены в {PARTICIPANTS_FILE}")

if __name__ == "__main__":
    add_test_users()

