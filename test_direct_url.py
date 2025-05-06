import requests
import time
import os
from datetime import datetime, timedelta

# الرابط الكامل الذي يعمل بشكل جيد
WORKING_URL_TEMPLATE = "http://172.16.16.13:8585/att/api/transactionReport/export/?export_headers=emp_code,first_name,dept_name,att_date,punch_time,punch_state,terminal_alias&start_date={start_date}&end_date={end_date}&departments=10&employees=-1&page_size=6000&export_type=txt&page=1&limit=6000"

# الرابط المستخدم في النظام
SYSTEM_URL = "http://172.16.16.13:8585/att/api/transactionReport/export/"

# إعدادات الاتصال
CONNECT_TIMEOUT = 10  # وقت مستقطع أقصر للاختبار
READ_TIMEOUT = 20     # وقت مستقطع أقصر للاختبار

def test_direct_url():
    """اختبار الرابط المباشر الكامل الذي يعمل بشكل جيد"""
    print("=== اختبار الرابط المباشر الكامل ===")
    
    # إعداد نطاق تاريخ الاختبار (اليوم والأمس)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # تنسيق التواريخ حسب متطلبات الرابط
    start_date = f"{yesterday.strftime('%Y-%m-%d')}%2000:00:00"
    end_date = f"{today.strftime('%Y-%m-%d')}%2023:59:59"
    
    # بناء الرابط الكامل
    full_url = WORKING_URL_TEMPLATE.format(start_date=start_date, end_date=end_date)
    
    print(f"استخدام الرابط: {full_url}")
    
    try:
        # محاولة الاتصال والحصول على البيانات
        start_time = time.time()
        response = requests.get(full_url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        elapsed_time = time.time() - start_time
        
        print(f"تم استلام استجابة في {elapsed_time:.2f} ثانية")
        print(f"رمز الحالة: {response.status_code}")
        
        if response.status_code == 200:
            print("تم الاتصال بنجاح!")
            content_preview = response.text[:200].replace('\n', '\\n')
            print(f"عينة من المحتوى: {content_preview}...")
            
            # حفظ الاستجابة في ملف للتحقق
            with open("direct_url_response.txt", "wb") as f:
                f.write(response.content)
                
            print("تم حفظ الاستجابة الكاملة في ملف direct_url_response.txt")
            return True
        else:
            print(f"فشل الاتصال مع رمز الحالة {response.status_code}")
            print(f"الاستجابة: {response.text}")
            return False
            
    except requests.exceptions.ConnectTimeout:
        print("خطأ: انتهت مهلة الاتصال")
    except requests.exceptions.ReadTimeout:
        print("خطأ: انتهت مهلة قراءة الاستجابة")
    except requests.exceptions.ConnectionError as e:
        print(f"خطأ في الاتصال: {e}")
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
        
    return False

def test_direct_url_with_auth():
    """اختبار الرابط المباشر الكامل مع مصادقة أساسية"""
    print("\n=== اختبار الرابط المباشر الكامل مع مصادقة أساسية ===")
    
    # إعداد نطاق تاريخ الاختبار (اليوم والأمس)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # تنسيق التواريخ حسب متطلبات الرابط
    start_date = f"{yesterday.strftime('%Y-%m-%d')}%2000:00:00"
    end_date = f"{today.strftime('%Y-%m-%d')}%2023:59:59"
    
    # بناء الرابط الكامل
    full_url = WORKING_URL_TEMPLATE.format(start_date=start_date, end_date=end_date)
    
    print(f"استخدام الرابط: {full_url}")
    
    # بيانات المصادقة - استخدم اسم المستخدم وكلمة المرور الفعلية للنظام
    username = "raghad"
    password = "A1111111"
    
    print(f"استخدام مصادقة أساسية مع المستخدم: {username}")
    
    try:
        # محاولة الاتصال والحصول على البيانات مع مصادقة أساسية
        start_time = time.time()
        response = requests.get(
            full_url, 
            auth=(username, password),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        elapsed_time = time.time() - start_time
        
        print(f"تم استلام استجابة في {elapsed_time:.2f} ثانية")
        print(f"رمز الحالة: {response.status_code}")
        
        if response.status_code == 200:
            print("تم الاتصال بنجاح!")
            content_preview = response.text[:200].replace('\n', '\\n')
            print(f"عينة من المحتوى: {content_preview}...")
            
            # حفظ الاستجابة في ملف للتحقق
            with open("direct_url_with_auth_response.txt", "wb") as f:
                f.write(response.content)
                
            print("تم حفظ الاستجابة الكاملة في ملف direct_url_with_auth_response.txt")
            return True
        else:
            print(f"فشل الاتصال مع رمز الحالة {response.status_code}")
            print(f"الاستجابة: {response.text}")
            return False
            
    except requests.exceptions.ConnectTimeout:
        print("خطأ: انتهت مهلة الاتصال")
    except requests.exceptions.ReadTimeout:
        print("خطأ: انتهت مهلة قراءة الاستجابة")
    except requests.exceptions.ConnectionError as e:
        print(f"خطأ في الاتصال: {e}")
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
        
    return False

def test_system_url():
    """اختبار الرابط المستخدم في النظام"""
    print("\n=== اختبار الرابط المستخدم في النظام ===")
    
    # اختبار الرابط الأساسي فقط
    print(f"استخدام الرابط: {SYSTEM_URL}")
    
    try:
        # محاولة الاتصال بدون معلمات
        start_time = time.time()
        response = requests.get(SYSTEM_URL, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        elapsed_time = time.time() - start_time
        
        print(f"تم استلام استجابة في {elapsed_time:.2f} ثانية")
        print(f"رمز الحالة: {response.status_code}")
        
        if response.status_code == 200:
            print("تم الاتصال بنجاح!")
            content_preview = response.text[:200].replace('\n', '\\n')
            print(f"عينة من المحتوى: {content_preview}...")
            return True
        else:
            print(f"فشل الاتصال مع رمز الحالة {response.status_code}")
            print(f"الاستجابة: {response.text}")
            
            # جرب الرابط نفسه مع معلمات تاريخ بسيطة
            print("\nمحاولة الرابط مع معلمات تاريخ بسيطة...")
            
            # إعداد نطاق تاريخ الاختبار (اليوم والأمس)
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            params = {
                "start_time": yesterday,
                "end_time": today,
                "dept_id": 10
            }
            
            try:
                response = requests.get(SYSTEM_URL, params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
                print(f"رمز الحالة: {response.status_code}")
                
                if response.status_code == 200:
                    print("نجح الاتصال مع المعلمات!")
                    content_preview = response.text[:200].replace('\n', '\\n')
                    print(f"عينة من المحتوى: {content_preview}...")
                    return True
                else:
                    print(f"فشل الاتصال مع رمز الحالة {response.status_code}")
                    print(f"الاستجابة: {response.text}")
            except Exception as e:
                print(f"خطأ عند المحاولة مع معلمات: {e}")
            
            return False
            
    except requests.exceptions.ConnectTimeout:
        print("خطأ: انتهت مهلة الاتصال")
    except requests.exceptions.ReadTimeout:
        print("خطأ: انتهت مهلة قراءة الاستجابة")
    except requests.exceptions.ConnectionError as e:
        print(f"خطأ في الاتصال: {e}")
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
        
    return False

def suggest_fixes():
    """اقتراح تحسينات على الكود الحالي"""
    print("\n=== الإصلاحات المقترحة ===")
    print("1. تحديث طريقة الاستعلام في sync_service.py للاستخدام المباشر للرابط الكامل بدلاً من إضافة المعلمات")
    print("2. التخلي عن المصادقة باستخدام /login إذا كان الرابط المباشر يعمل بدون مصادقة")
    print("3. تحديث تنسيق التواريخ لتطابق الصيغة المطلوبة")
    print("4. استخدام معلمات export_headers و export_type و page_size و limit المناسبة")
    
    print("\nنموذج للكود المقترح:")
    code_example = '''
    def get_attendance_data(start_date, end_date, dept_id=10):
        """الحصول على بيانات الحضور باستخدام الرابط المباشر"""
        # تنسيق التواريخ
        start_str = f"{start_date.strftime('%Y-%m-%d')}%2000:00:00"
        end_str = f"{end_date.strftime('%Y-%m-%d')}%2023:59:59"
        
        # بناء الرابط الكامل
        url = f"http://172.16.16.13:8585/att/api/transactionReport/export/?export_headers=emp_code,first_name,dept_name,att_date,punch_time,punch_state,terminal_alias&start_date={start_str}&end_date={end_str}&departments={dept_id}&employees=-1&page_size=6000&export_type=txt&page=1&limit=6000"
        
        try:
            response = requests.get(url, timeout=(30, 180))
            if response.status_code == 200:
                # حفظ الاستجابة في ملف مؤقت
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                logger.error(f"فشل الحصول على البيانات: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"خطأ أثناء الاتصال بـ API: {str(e)}")
            return False
    '''
    print(code_example)

if __name__ == "__main__":
    print("اختبار الاتصال بـ BioTime API")
    print("============================")
    
    # اختبار الرابط المباشر الكامل
    direct_result = test_direct_url()
    
    # اختبار الرابط المباشر الكامل مع مصادقة أساسية
    direct_auth_result = test_direct_url_with_auth()
    
    # اختبار الرابط المستخدم في النظام
    system_result = test_system_url()
    
    print("\n=== النتيجة النهائية ===")
    if direct_result:
        print("✓ الرابط المباشر الكامل يعمل بشكل جيد")
    else:
        print("✗ الرابط المباشر الكامل لا يعمل")
        
    if direct_auth_result:
        print("✓ الرابط المباشر الكامل مع مصادقة أساسية يعمل بشكل جيد")
    else:
        print("✗ الرابط المباشر الكامل مع مصادقة أساسية لا يعمل")
        
    if system_result:
        print("✓ الرابط المستخدم في النظام يعمل")
    else:
        print("✗ الرابط المستخدم في النظام لا يعمل")
    
    # اقتراح إصلاحات
    suggest_fixes()