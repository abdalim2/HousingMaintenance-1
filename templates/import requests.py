import requests

url = "http://172.16.16.13:8585/att/api/transactionReport/export/?export_headers=emp_code,first_name,dept_name,att_date,punch_time,punch_state,terminal_alias&start_date=2025-04-01%2000:00:00&end_date=2025-04-02%2023:59:59&departments=10&employees=-1&page_size=6000&export_type=txt&page=1&limit=6000"

# Using Basic Authentication with username and password
username = "raghad"
password = "A1111111"

# Remove the headers and use auth parameter instead
response = requests.get(url, auth=(username, password))

if response.status_code == 200:
    print("Success!")
    # عرض البيانات في موجه الأوامر
    print("--- البيانات المسحوبة ---")
    print(response.text)
    
    # يمكنك أيضًا حفظ البيانات في ملف مع عرضها
    with open("attendance_data.txt", "w", encoding="utf-8") as file:
        file.write(response.text)
    print("تم حفظ البيانات في ملف attendance_data.txt")
else:
    print(f"Failed with status code: {response.status_code}")
    print(response.text)