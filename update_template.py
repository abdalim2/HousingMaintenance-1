import re

def update_template():
    # Read the template file
    with open("templates/timesheet.html", "r") as f:
        content = f.read()
    
    # Replace dot notation with dictionary access for day.record attributes
    content = content.replace('day.record.clock_in', "day.record['clock_in']")
    content = content.replace('day.record.clock_out', "day.record['clock_out']")
    content = content.replace('day.record.work_hours', "day.record['work_hours']")
    content = content.replace('day.record.overtime_hours', "day.record['overtime_hours']")
    
    # Write the updated template file
    with open("templates/timesheet.html", "w") as f:
        f.write(content)
    
    print("Template updated successfully.")

if __name__ == '__main__':
    update_template()
