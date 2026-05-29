import csv
import os

COLUMNS = ['title', 'encrypted_password', 'url', 'notes']

def init_file(filepath: str):
    if not os.path.exists(filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()

def load_entries(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def save_entries(filepath: str, entries: list):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(entries)

def add_entry(filepath: str, title: str, enc_password: str,
              url: str, notes: str):
    entries = load_entries(filepath)
    entries.append({
        'title': title,
        'encrypted_password': enc_password,
        'url': url,
        'notes': notes
    })
    save_entries(filepath, entries)

def find_entries(filepath: str, query: str) -> list:
    entries = load_entries(filepath)
    q = query.lower()
    return [e for e in entries if q in e['title'].lower()]

def update_entry(filepath: str, title: str, enc_password: str,
                 url: str, notes: str) -> bool:
    entries = load_entries(filepath)
    for e in entries:
        if e['title'].lower() == title.lower():
            e['encrypted_password'] = enc_password
            e['url'] = url
            e['notes'] = notes
            save_entries(filepath, entries)
            return True
    return False

def delete_entry(filepath: str, title: str) -> bool:
    entries = load_entries(filepath)
    new = [e for e in entries if e['title'].lower() != title.lower()]
    if len(new) == len(entries):
        return False
    save_entries(filepath, new)
    return True