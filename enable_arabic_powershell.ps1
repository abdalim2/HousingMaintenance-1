# تمكين دعم اللغة العربية في PowerShell
# هذا الملف يحتوي على أوامر لتغيير إعدادات PowerShell لدعم اللغة العربية

# تغيير ترميز الإدخال والإخراج إلى UTF-8
[console]::OutputEncoding = [System.Text.Encoding]::UTF8
[console]::InputEncoding = [System.Text.Encoding]::UTF8

# تغيير ترميز الصفحة إلى UTF-8
chcp 65001

# علامات تحكم خاصة للنص العربي
$RTL_MARK = [char]0x200F  # علامة النص من اليمين إلى اليسار
$LTR_MARK = [char]0x200E  # علامة النص من اليسار إلى اليمين
$ZWJ = [char]0x200D      # علامة وصل بدون عرض

# تعيين القيم الافتراضية للإخراج إلى UTF-8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# إضافة هذه الإعدادات إلى ملف تعريف المستخدم الخاص بـ PowerShell
# إنشاء ملف التعريف إذا لم يكن موجوداً
if (!(Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force
    Write-Host "$($RTL_MARK)تم إنشاء ملف تعريف PowerShell جديد" -ForegroundColor Green
}

# تعريف وظيفة لعرض النص العربي بشكل صحيح
function Write-Arabic {
    param(
        [string]$Text,
        [string]$ForegroundColor = "White"
    )
    Write-Host "$($RTL_MARK)$Text" -ForegroundColor $ForegroundColor
}

# إضافة إعدادات اللغة العربية إلى ملف التعريف
$profileContent = @"
# تمكين دعم اللغة العربية
[console]::OutputEncoding = [System.Text.Encoding]::UTF8
[console]::InputEncoding = [System.Text.Encoding]::UTF8
`$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
`$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# علامات تحكم خاصة للنص العربي
`$RTL_MARK = [char]0x200F  # علامة النص من اليمين إلى اليسار
`$LTR_MARK = [char]0x200E  # علامة النص من اليسار إلى اليمين
`$ZWJ = [char]0x200D      # علامة وصل بدون عرض

# وظيفة مساعدة لعرض النص العربي بشكل صحيح
function Write-Arabic {
    param(
        [string]`$Text,
        [string]`$ForegroundColor = "White"
    )
    Write-Host "`$(`$RTL_MARK)`$Text" -ForegroundColor `$ForegroundColor
}

# وظيفة لتصحيح عرض النص العربي في الأمر Echo
function Echo-Arabic {
    param([string]`$Text)
    Echo "`$([char]0x200F)`$Text"
}

# تجاوز الأمر Echo الأصلي لإضافة دعم أفضل للغة العربية
function global:Echo {
    param([string]`$Text)
    if (`$Text -match '[\u0600-\u06FF]') {
        Echo-Arabic `$Text
    } else {
        Microsoft.PowerShell.Utility\Echo `$Text
    }
}
"@

Add-Content -Path $PROFILE -Value $profileContent -Encoding UTF8

# نصائح لتحسين دعم اللغة العربية
Write-Host "`n=== تعليمات مفيدة لدعم اللغة العربية ===`n" -ForegroundColor Cyan

Write-Arabic "1. استخدم دائمًا الرمز الخاص قبل النصوص العربية" "Yellow"
Write-Host "   $([char]0x200F)نص عربي" -ForegroundColor White

Write-Arabic "2. في Python أضف الرمز \u200F قبل النصوص العربية:" "Yellow"
Write-Host '   print("\u200Fنص عربي")' -ForegroundColor White

Write-Arabic "3. لتصحيح عرض النص العربي في سطر الأوامر، استخدم:" "Yellow"
Write-Host "   Echo-Arabic `"النص العربي`"" -ForegroundColor White

Write-Arabic "4. تحقق من تكوين محرر النصوص للتأكد من أنه يدعم UTF-8" "Yellow"

Write-Arabic "5. في ملفات HTML، استخدم dir=rtl للعناصر العربية:" "Yellow"
Write-Host '   <div dir="rtl">نص عربي</div>' -ForegroundColor White

Write-Arabic "`n=== إجراءات فورية لإصلاح مشكلة النص المعكوس ===`n" "Green"

# تحديث جميع ملفات Python لتضمين علامات RTL
$pythonFilesWithArabic = Get-ChildItem -Path "d:\CPC holding co\Sacodeco Housing - General\BiometricSync" -Filter "*.py" | Where-Object { 
    $content = Get-Content -Path $_.FullName -Raw -ErrorAction SilentlyContinue
    $content -match '[\u0600-\u06FF]'
}

if ($pythonFilesWithArabic) {
    Write-Arabic "تم العثور على ملفات Python تحتوي على نصوص عربية:" "Magenta"
    foreach ($file in $pythonFilesWithArabic) {
        Write-Host "   - $($file.Name)" -ForegroundColor White
    }
    
    Write-Arabic "`nلتصحيح عرض النصوص العربية في هذه الملفات، أضف '\u200F' قبل كل نص عربي." "Yellow"
    Write-Arabic "مثال:" "White"
    Write-Host '   arabic_text = "\u200Fنص عربي"' -ForegroundColor White
    Write-Host '   print(f"\u200Fمرحباً {name}")' -ForegroundColor White
}

# اختبار النص العربي
Write-Arabic "`n=== اختبار العرض ===`n" "Cyan"
Write-Arabic "اختبار النص العربي: هذا نص باللغة العربية" "Green"

# إنشاء ملف مساعدة منفصل للتعامل مع النص العربي في Python
$pythonHelperContent = @"
# -*- coding: utf-8 -*-
# arabic_helper.py - وظائف مساعدة للتعامل مع النصوص العربية في Python

# علامات تحكم خاصة للنص العربي
RTL_MARK = "\u200F"  # علامة النص من اليمين إلى اليسار
LTR_MARK = "\u200E"  # علامة النص من اليسار إلى اليمين

def arabic_text(text):
    """
    تضيف علامة RTL إلى النص العربي لعرضه بشكل صحيح
    
    Args:
        text (str): النص العربي المراد عرضه
        
    Returns:
        str: النص مع علامة RTL
    """
    return RTL_MARK + text

def arabic_print(text, *args, **kwargs):
    """
    تطبع نصًا عربيًا مع إضافة علامة RTL
    """
    print(RTL_MARK + text, *args, **kwargs)

def fix_arabic_in_dict(data_dict):
    """
    تصحيح جميع النصوص العربية في قاموس
    """
    for key, value in data_dict.items():
        if isinstance(value, str) and any(ord(c) >= 0x600 and ord(c) <= 0x6FF for c in value):
            data_dict[key] = RTL_MARK + value
    return data_dict
"@

Set-Content -Path "d:\CPC holding co\Sacodeco Housing - General\BiometricSync\arabic_helper.py" -Value $pythonHelperContent -Encoding UTF8
Write-Arabic "تم إنشاء ملف 'arabic_helper.py' للمساعدة في دعم اللغة العربية في Python" "Green"

# إنشاء ملف JavaScript للتعامل مع النص العربي في المتصفح
$jsHelperContent = @"
/**
 * arabic_helper.js - وظائف مساعدة للتعامل مع النصوص العربية في JavaScript
 */

// علامات تحكم خاصة للنص العربي
const RTL_MARK = "\u200F";  // علامة النص من اليمين إلى اليسار
const LTR_MARK = "\u200E";  // علامة النص من اليسار إلى اليمين

/**
 * تضيف علامة RTL إلى النص العربي لعرضه بشكل صحيح
 * @param {string} text - النص العربي المراد عرضه
 * @return {string} النص مع علامة RTL
 */
function arabicText(text) {
    return RTL_MARK + text;
}

/**
 * تطبق اتجاه RTL على جميع العناصر العربية في الصفحة
 */
function fixArabicDisplay() {
    // حدد جميع العناصر التي تحتوي على نص عربي
    const arabicRegex = /[\u0600-\u06FF]/;
    const textNodes = [];
    
    function findTextNodes(element) {
        if (element.nodeType === Node.TEXT_NODE) {
            if (arabicRegex.test(element.nodeValue)) {
                textNodes.push(element);
            }
        } else {
            for (let i = 0; i < element.childNodes.length; i++) {
                findTextNodes(element.childNodes[i]);
            }
        }
    }
    
    findTextNodes(document.body);
    
    // أضف علامة RTL إلى النصوص العربية
    for (let node of textNodes) {
        if (!node.parentElement.hasAttribute('dir')) {
            node.parentElement.setAttribute('dir', 'rtl');
        }
        if (!node.nodeValue.startsWith(RTL_MARK)) {
            node.nodeValue = RTL_MARK + node.nodeValue;
        }
    }
}

// تنفيذ الدالة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', fixArabicDisplay);
"@

# إنشاء دليل JavaScript إذا لم يكن موجوداً
$jsPath = "d:\CPC holding co\Sacodeco Housing - General\BiometricSync\static\js"
if (!(Test-Path -Path $jsPath)) {
    New-Item -ItemType Directory -Path $jsPath -Force | Out-Null
}

Set-Content -Path "$jsPath\arabic_helper.js" -Value $jsHelperContent -Encoding UTF8
Write-Arabic "تم إنشاء ملف 'arabic_helper.js' للمساعدة في دعم اللغة العربية في المتصفح" "Green"

# اختبار الإعدادات
Write-Arabic "`nاكتب أي نص عربي للتحقق من عرضه بشكل صحيح. (اكتب 'خروج' للإنهاء):" "Magenta"
do {
    $testText = Read-Host
    if ($testText -ne "خروج" -and $testText -ne "exit") {
        Write-Arabic $testText "Green"
        Write-Host "$([char]0x200F)$testText" -ForegroundColor Yellow
    }
} while ($testText -ne "خروج" -and $testText -ne "exit")