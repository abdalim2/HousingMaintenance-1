"""
سكريبت لإصلاح سجلات البصمات المتطابقة حيث أوقات الدخول والخروج متساوية
ومعالجة مشكلة البصمات العكسية (عندما تكون بصمة الخروج قبل بصمة الدخول)
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy import text
from database import db, init_db

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """إنشاء تطبيق Flask للعمليات على قاعدة البيانات"""
    app = Flask(__name__