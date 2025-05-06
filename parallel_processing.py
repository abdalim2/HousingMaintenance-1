
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging

# إعداد التسجيل
logger = logging.getLogger(__name__)

def parallel_process_data(data_lines, header, column_indices, process_batch_size=100, max_workers=4):
    """
    معالجة البيانات بشكل متوازي لتسريع عملية المزامنة
    
    Args:
        data_lines (list): قائمة من سطور البيانات
        header (list): ترويسة البيانات
        column_indices (dict): فهرس الأعمدة
        process_batch_size (int): حجم دفعة المعالجة
        max_workers (int): الحد الأقصى لعدد المعالجات المتوازية
    
    Returns:
        list: قائمة السجلات المعالجة
    """
    # تقسيم البيانات إلى دفعات
    total_lines = len(data_lines)
    batch_count = (total_lines + process_batch_size - 1) // process_batch_size
    batches = np.array_split(data_lines, batch_count)
    
    logger.info(f"تقسيم {total_lines} سطر إلى {len(batches)} دفعة للمعالجة المتوازية")
    
    # دالة لمعالجة دفعة واحدة من البيانات
    def process_batch(batch):
        result = []
        for line in batch:
            try:
                line = line.strip()
                if not line:
                    continue
                
                fields = line.split(',')
                if len(fields) < len(header):
                    continue
                
                # بناء قاموس من البيانات
                record = {
                    'emp_code': fields[column_indices['emp_code']],
                    'first_name': fields[column_indices['first_name']] if 'first_name' in column_indices else '',
                    'last_name': fields[column_indices['last_name']] if 'last_name' in column_indices else '',
                    'dept_name': fields[column_indices['dept_name']],
                    'att_date': fields[column_indices['att_date']],
                    'punch_time': fields[column_indices['punch_time']],
                    'punch_state': fields[column_indices['punch_state']],
                    'terminal_alias': fields[column_indices['terminal_alias']]
                }
                
                result.append(record)
            except Exception as e:
                logger.error(f"خطأ في معالجة السطر: {str(e)}")
                
        return result
    
    # معالجة الدفعات بشكل متوازي
    all_records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch_results = list(executor.map(process_batch, batches))
        
    # دمج النتائج
    for batch in batch_results:
        all_records.extend(batch)
    
    logger.info(f"تمت معالجة {len(all_records)} سجل بشكل متوازي")
    return all_records
