import requests
import sys

file_path = "inventory_data.csv"

try:
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f, 'text/csv')}
        response = requests.post('http://localhost:3000/api/upload', files=files)
        
        print("=" * 60)
        print("📤 FILE UPLOAD RESULT")
        print("=" * 60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ " + data.get('message', 'Upload successful!'))
                print(f"📊 Rows: {data.get('rows', 0)}")
                print(f"📋 Columns: {', '.join(data.get('columns', []))}")
            else:
                print("❌ Error: " + data.get('message', 'Unknown error'))
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
except FileNotFoundError:
    print("❌ File not found! Please make sure inventory_data.csv exists")
except Exception as e:
    print(f"❌ Error: {e}")
    
print("=" * 60)
print("🌐 Open http://localhost:3000 to see your data!")
print("=" * 60)
