# -*- coding: utf-8 -*-
"""
مكتبة مساعدة للتعامل مع النص العربي في Python
"""

# علامة RTL للنص العربي (من اليمين إلى اليسار)
RTL_MARK = "\u200F"

def arabic_text(text):
    """إضافة علامة RTL للنص العربي ليظهر بشكل صحيح"""
    return RTL_MARK + text

def arabic_print(text):
    """طباعة نص عربي بشكل صحيح"""
    print(RTL_MARK + text)

# مثال على الاستخدام
if __name__ == "__main__":
    arabic_print("هذا مثال على نص عربي يظهر بشكل صحيح")
    text = arabic_text("مرحبا بالعالم")
    print(text)