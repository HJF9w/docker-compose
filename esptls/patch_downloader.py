import re

with open('/home/net/git/docker-compose/esptls/downloader/downloader.py', 'r') as f:
    content = f.read()

# Fix the delete logic and handle already synced files
content = content.replace('''
        if name in synced:
            continue
            
        new_count += 1
''', '''
        if name in synced:
            # Try to delete it again if it was protected before
            try:
                del_r = requests.get(f'http://{ESP_IP}/file_delete?path=/{name}', timeout=10)
                if del_r.status_code == 200 and "Error" not in del_r.text:
                    print(f"Successfully deleted previously synced file {name}")
            except Exception as e:
                pass
            continue
            
        new_count += 1
''')

content = content.replace('''
                if del_r.status_code == 200:
                    add_synced_file(name)
                    print(f"Successfully synced and deleted {name}")
                else:
                    print(f"Warning: Downloaded {name} but failed to delete from ESP (Status: {del_r.status_code})")
''', '''
                if del_r.status_code == 200 and "Error" not in del_r.text:
                    add_synced_file(name)
                    print(f"Successfully synced and deleted {name}")
                else:
                    add_synced_file(name)
                    print(f"Warning: Downloaded {name} but failed to delete from ESP. (Will retry later) Response: {del_r.text}")
''')

with open('/home/net/git/docker-compose/esptls/downloader/downloader.py', 'w') as f:
    f.write(content)
