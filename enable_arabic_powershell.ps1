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
    param([string]`$Text, [string]`$ForegroundColor = "White")
    Write-Host "`$(`$RTL_MARK)`$Text" -ForegroundColor `$ForegroundColor
}
"@

Add-Content -Path $PROFILE -Value $profileContent -Encoding UTF8

# تعريف وظيفة لعرض النص العربي بشكل صحيح
function Write-Arabic {
    param([string]$Text, [string]$ForegroundColor = "White")
    Write-Host "$($RTL_MARK)$Text" -ForegroundColor $ForegroundColor
}

# تثبيت وحدة مفيدة للتعامل مع النص العربي إذا كانت غير موجودة
$requiredModule = "StringFormatting"
if (-not (Get-Module -ListAvailable -Name $requiredModule)) {
    Write-Host "جاري محاولة تثبيت وحدة $requiredModule لتحسين دعم اللغة العربية..." -ForegroundColor Yellow
    try {
        Install-Module -Name $requiredModule -Force -AllowClobber -Scope CurrentUser -ErrorAction Stop
        Write-Host "تم تثبيت وحدة $requiredModule بنجاح" -ForegroundColor Green
    }
    catch {
        Write-Host "لم يتم تثبيت وحدة $requiredModule. قد تحتاج إلى تثبيتها يدوياً: Install-Module -Name $requiredModule -Force" -ForegroundColor Red
    }
}

# نصائح لتحسين دعم اللغة العربية
Write-Host "`n=== تعليمات مفيدة لدعم اللغة العربية ===`n" -ForegroundColor Cyan

Write-Arabic "1. قم بتغيير خط وحدة التحكم PowerShell إلى خط يدعم اللغة العربية مثل:" "Yellow"
Write-Host "   - Courier New" -ForegroundColor White 
Write-Host "   - Arial" -ForegroundColor White
Write-Host "   - Microsoft Sans Serif" -ForegroundColor White
Write-Host "   - Traditional Arabic" -ForegroundColor White
Write-Arabic "   يمكنك القيام بذلك عن طريق النقر بزر الماوس الأيمن على شريط عنوان PowerShell > خصائص > خط" "Gray"

Write-Arabic "`n2. استخدم الوظيفة الجديدة Write-Arabic لعرض النص العربي بشكل صحيح:" "Yellow"
Write-Host "   Write-Arabic `"النص العربي الخاص بك`"" -ForegroundColor White

Write-Arabic "`n3. عند تشغيل نصوص Python التي تحتوي على نص عربي، استخدم:" "Yellow"
Write-Host "   python -X utf8 your_script.py" -ForegroundColor White

Write-Arabic "`n4. إعادة تشغيل PowerShell لتطبيق الإعدادات الجديدة بشكل كامل" "Yellow"

Write-Arabic "`n5. تفعيل دعم PowerShell Core لعرض أفضل للغة العربية:" "Yellow"
Write-Host "   قم بتثبيت PowerShell 7 من الموقع الرسمي:" -ForegroundColor White
Write-Host "   https://aka.ms/powershell-release?tag=stable" -ForegroundColor White

Write-Arabic "`n=== تم إعداد PowerShell لدعم اللغة العربية! ===" "Green"

# اختبار الإعدادات
Write-Arabic "`nاختبار دعم اللغة العربية:" "Magenta"
Write-Arabic "هذا نص باللغة العربية للتأكد من أن الإعدادات تعمل بشكل صحيح" "White"

# تعديل ملفات Python ليستخدموا علامات اتجاه النص
Write-Arabic "`nهل تريد تعديل ملفات Python للاستخدام المثالي مع اللغة العربية؟ (نعم/لا)" "Yellow"
$response = Read-Host

if ($response -eq "نعم" -or $response -eq "ن" -or $response -eq "y" -or $response -eq "yes") {
    # تعديل الملفات التي تحتوي على نص عربي
    try {
        $syncServicePath = "d:\CPC holding co\Sacodeco Housing - General\BiometricSync\sync_service.py"
        if (Test-Path $syncServicePath) {
            $content = Get-Content $syncServicePath -Raw -Encoding UTF8
            # إضافة تعريف علامات الاتجاه في بداية الملف
            if (-not $content.Contains("RTL_MARK")) {
                $RTL_CODE = @"
# علامات خاصة للتحكم في اتجاه النص العربي
RTL_MARK = '\u200F'  # علامة النص من اليمين إلى اليسار
LTR_MARK = '\u200E'  # علامة النص من اليسار إلى اليمين

"@
                $content = $RTL_CODE + $content
                # تطبيق علامة RTL على النصوص العربية
                $content = $content -replace '("[\u0600-\u06FF\s]+?")', '"' + $RTL_MARK + '\1'
                Set-Content -Path $syncServicePath -Value $content -Encoding UTF8
                Write-Arabic "تم تعديل ملف $syncServicePath لدعم اللغة العربية بشكل أفضل" "Green"
            }
            else {
                Write-Arabic "ملف $syncServicePath يحتوي بالفعل على تعريفات لدعم اتجاه النص العربي" "Yellow"
            }
        }
    }
    catch {
        Write-Arabic "حدث خطأ أثناء محاولة تعديل ملفات Python: $_" "Red"
    }
}