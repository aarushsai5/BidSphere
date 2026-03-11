import sqlite3
import os
import requests
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def update_admin(new_username, new_password):
    token = os.environ.get('BLOB_READ_WRITE_TOKEN')
    if not token:
        print("Error: BLOB_READ_WRITE_TOKEN not found in .env file.")
        return

    BLOB_URL = "https://blob.vercel-storage.com/auction.db"
    temp_db_path = "temp_auction.db"

    print("Downloading the live database from Vercel Blob...")
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(BLOB_URL, headers=headers)
    
    if res.status_code == 200:
        with open(temp_db_path, 'wb') as f:
            f.write(res.content)
        print("Live database downloaded successfully.")
    else:
        print("Live database not found or access denied. Please ensure the app is running first.")
        return

    print(f"Assigning new credentials (Username: {new_username})...")
    conn = sqlite3.connect(temp_db_path)
    c = conn.cursor()
    
    # Try to find the existing admin user
    admin_user = c.execute('SELECT id FROM users WHERE role = "admin"').fetchone()
    
    hashed_password = generate_password_hash(new_password)
    
    if admin_user:
        c.execute('UPDATE users SET username = ?, password = ? WHERE id = ?', (new_username, hashed_password, admin_user[0]))
    else:
        # If no admin exists for some reason, create one
        c.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, "admin")', 
                  (new_username, f"{new_username}@admin.com", hashed_password))
    
    conn.commit()
    conn.close()

    print("Uploading updated database back to Vercel Blob...")
    with open(temp_db_path, 'rb') as f:
        upload_headers = {
            'Authorization': f'Bearer {token}',
            'x-api-version': '7'
        }
        upload_res = requests.put(BLOB_URL, headers=upload_headers, data=f)
        
        if upload_res.status_code == 200:
            print("Successfully updated admin credentials on the live site!")
        else:
            print(f"Failed to upload: {upload_res.status_code} - {upload_res.text}")

    # Cleanup temporary local DB file
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

if __name__ == "__main__":
    print("--- Auction Management System Admin Updater ---")
    new_user = input("Enter the new admin username: ").strip()
    new_pass = input("Enter the new admin password: ").strip()
    
    if new_user and new_pass:
        update_admin(new_user, new_pass)
    else:
        print("Username and password cannot be empty.")
