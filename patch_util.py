
import os
import re
import logging
import shutil

# إعداد التسجيل
logger = logging.getLogger(__name__)

def patch_file(file_path, patches):
    """
    تطبيق مجموعة من التعديلات على ملف
    
    Args:
        file_path (str): مسار الملف المراد تعديله
        patches (list): قائمة من التعديلات على شكل {"search": "...", "replace": "...", "description": "..."}
    
    Returns:
        bool: True إذا تم التعديل بنجاح، False إذا فشل
    """
    try:
        # التأكد من وجود الملف
        if not os.path.exists(file_path):
            logger.error(f"الملف غير موجود: {file_path}")
            return False
        
        # عمل نسخة احتياطية من الملف
        backup_path = f"{file_path}.bak.old"
        shutil.copy2(file_path, backup_path)
        logger.info(f"تم إنشاء نسخة احتياطية: {backup_path}")
        
        # قراءة محتوى الملف
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # تطبيق التعديلات
        patched_content = content
        applied_patches = 0
        
        for patch in patches:
            search = patch['search']
            replace = patch['replace']
            description = patch['description']
            
            if search in patched_content:
                patched_content = patched_content.replace(search, replace)
                applied_patches += 1
                logger.info(f"تم تطبيق التعديل: {description}")
            else:
                logger.warning(f"لم يتم العثور على النمط: {search}")
        
        # كتابة المحتوى المعدل
        if applied_patches > 0:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(patched_content)
            logger.info(f"تم تطبيق {applied_patches} من {len(patches)} تعديل")
            return True
        else:
            logger.warning("لم يتم تطبيق أي تعديلات")
            return False
            
    except Exception as e:
        logger.error(f"خطأ أثناء تعديل الملف: {str(e)}")
        return False
