#!/usr/bin/env python
"""
Script para mejorar la selección de departamentos en la aplicación
1. Reemplaza la carga de DEPARTMENTS en sync_service.py para asegurar que se usen los valores de la configuración
2. Modifica la interfaz de selección de departamentos para usar un selector múltiple en lugar de un input de texto
"""
import os
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_departments_variable():
    """Mejora la carga de la variable DEPARTMENTS en sync_service.py"""
    try:
        sync_service_path = 'd:\\HousingMaintenance\\HousingMaintenance-4\\sync_service.py'
        
        # Leer el archivo sync_service.py
        with open(sync_service_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Buscar y reemplazar la línea DEPARTMENTS = [10]
        old_line = 'DEPARTMENTS = [10]  # تحديث رقم القسم ليطابق الرابط الجديد'
        new_line = '''# Use environment variable for departments if available
dept_str = os.environ.get("DEPARTMENTS", "10")
try:
    DEPARTMENTS = [int(d.strip()) for d in dept_str.split(',') if d.strip().isdigit()]
    if not DEPARTMENTS:  # Fallback if no valid department IDs
        DEPARTMENTS = [10]
except Exception as e:
    DEPARTMENTS = [10]  # Fallback to department 10 by default
    logger.error(f"Error parsing DEPARTMENTS: {e}")

logger.info(f"Using departments: {DEPARTMENTS}")  # Log which departments are being used'''
        
        # Reemplazar la línea
        if old_line in content:
            updated_content = content.replace(old_line, new_line)
            
            # Guardar archivo actualizado
            with open(sync_service_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
                
            logger.info("Se actualizó la carga de la variable DEPARTMENTS en sync_service.py")
        else:
            logger.warning("No se pudo encontrar la línea DEPARTMENTS = [10] en sync_service.py")
    
    except Exception as e:
        logger.error(f"Error al modificar sync_service.py: {str(e)}")
        raise

def fix_departments_selector():
    """Modifica el template para usar un selector múltiple de departamentos"""
    try:
        template_path = 'd:\\HousingMaintenance\\HousingMaintenance-4\\templates\\settings.html'
        
        # Leer el archivo settings.html
        with open(template_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Identificar el bloque a reemplazar
        old_block = '''<div class="mb-3">
                        <label for="departments" class="form-label">{{ t('departments') }} (comma-separated IDs)</label>
                        <input type="text" class="form-control" id="departments" name="departments" value="{{ sync_settings.departments }}">
                        <div class="form-text">Example: 11,6,3,18,15,19,23,10,9,5,4,26,21</div>
                    </div>'''
        
        # Crear el nuevo bloque con selector múltiple
        new_block = '''<div class="mb-3">
                        <label for="departments" class="form-label">{{ t('departments') }}</label>
                        <select class="form-select" id="departments" name="departments" multiple size="5">
                            {% for dept in all_departments %}
                            <option value="{{ dept.id }}" {% if dept.id|string in sync_settings.selected_departments %}selected{% endif %}>
                                {{ dept.name }} (ID: {{ dept.id }})
                            </option>
                            {% endfor %}
                        </select>
                        <div class="form-text">{{ t('select_multiple_departments') }}</div>
                        <input type="hidden" name="departments_list" id="departments_list" value="{{ sync_settings.departments }}">
                    </div>
                    
                    <script>
                    // Script para actualizar el input hidden con los departamentos seleccionados
                    document.addEventListener('DOMContentLoaded', function() {
                        var deptSelect = document.getElementById('departments');
                        var deptsList = document.getElementById('departments_list');
                        
                        // Actualizar el input hidden cuando cambie la selección
                        deptSelect.addEventListener('change', function() {
                            var selectedValues = Array.from(deptSelect.selectedOptions).map(opt => opt.value).join(',');
                            deptsList.value = selectedValues;
                        });
                        
                        // Inicializar el input hidden con los valores actuales
                        var selectedValues = Array.from(deptSelect.selectedOptions).map(opt => opt.value).join(',');
                        deptsList.value = selectedValues;
                    });
                    </script>'''
        
        # Reemplazar el bloque en el archivo
        if old_block in content:
            updated_content = content.replace(old_block, new_block)
            
            # Guardar archivo actualizado
            with open(template_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
                
            logger.info("Se actualizó el selector de departamentos en settings.html")
        else:
            logger.warning("No se pudo encontrar el bloque del selector de departamentos en settings.html")
    
    except Exception as e:
        logger.error(f"Error al modificar settings.html: {str(e)}")
        raise

def update_settings_route():
    """Actualiza la ruta de settings para pasar los departamentos a la plantilla"""
    try:
        app_path = 'd:\\HousingMaintenance\\HousingMaintenance-4\\app.py'
        
        # Leer el archivo app.py
        with open(app_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Búsqueda por el bloque de código existente en la función settings
        old_block = '''    # Get housings and biometric terminals for settings page
    try:
        housings = Housing.query.all()
        terminals = BiometricTerminal.query.all()
    except Exception as e:
        app.logger.error(f"Error fetching housings and terminals: {str(e)}")
        housings = []
        terminals = []
    
    # Check if mock mode is enabled
    mock_mode_enabled = os.environ.get("MOCK_MODE", "false").lower() == "true" or sync_service.MOCK_MODE_ENABLED
    
    return render_template('settings.html', 
                          sync_settings=sync_settings, 
                          last_sync=last_sync,
                          housings=housings,
                          terminals=terminals,
                          mock_mode_enabled=mock_mode_enabled)'''
        
        # Crear el bloque actualizado incluyendo los departamentos
        new_block = '''    # Get housings and biometric terminals for settings page
    try:
        housings = Housing.query.all()
        terminals = BiometricTerminal.query.all()
        
        # Get all departments for the selector
        all_departments = Department.query.all()
        
        # Parse selected departments from the environment or sync_service
        selected_departments = []
        if current_depts:
            selected_departments = [d.strip() for d in current_depts.split(',') if d.strip().isdigit()]
    except Exception as e:
        app.logger.error(f"Error fetching housings and terminals: {str(e)}")
        housings = []
        terminals = []
        all_departments = []
        selected_departments = []
    
    # Check if mock mode is enabled
    mock_mode_enabled = os.environ.get("MOCK_MODE", "false").lower() == "true" or sync_service.MOCK_MODE_ENABLED
    
    # Add selected departments to the sync_settings
    sync_settings['selected_departments'] = selected_departments
    
    return render_template('settings.html', 
                          sync_settings=sync_settings, 
                          last_sync=last_sync,
                          housings=housings,
                          terminals=terminals,
                          all_departments=all_departments,
                          mock_mode_enabled=mock_mode_enabled)'''
        
        # Reemplazar el bloque
        if old_block in content:
            updated_content = content.replace(old_block, new_block)
            
            # Guardar archivo actualizado
            with open(app_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
                
            logger.info("Se actualizó la ruta settings en app.py")
        else:
            logger.warning("No se pudo encontrar el bloque del código en la función settings")
    
    except Exception as e:
        logger.error(f"Error al modificar app.py: {str(e)}")
        raise

def update_save_settings_route():
    """Actualiza la función save_settings para manejar el nuevo selector de departamentos"""
    try:
        app_path = 'd:\\HousingMaintenance\\HousingMaintenance-4\\app.py'
        
        # Leer el archivo app.py
        with open(app_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Buscar el bloque donde está la lógica para los departamentos
        old_block = '''        if 'departments' in request.form and request.form.get('departments'):
            departments = request.form.get('departments').strip()
            # Parse comma-separated department list
            try:
                dept_list = []
                for d in departments.split(','):
                    if d.strip().isdigit():
                        dept_list.append(int(d.strip()))
                
                if dept_list:  # Only update if at least one valid department ID
                    sync_service.DEPARTMENTS = dept_list
                    os.environ['DEPARTMENTS'] = departments  # Fix: use correct environment variable name
                    logger.info(f"Departments updated to: {dept_list}")
                else:
                    flash('No valid department IDs provided, using default departments', 'warning')
            except Exception as dept_e:
                flash(f'Error parsing departments: {str(dept_e)}', 'warning')
                logger.error(f"Error parsing departments: {str(dept_e)}")'''
        
        # Crear el bloque actualizado con mejor manejo del selector múltiple
        new_block = '''        # Procesamos el campo departments_list en lugar del campo departments
        if 'departments_list' in request.form and request.form.get('departments_list'):
            departments = request.form.get('departments_list').strip()
            # Parse comma-separated department list
            try:
                dept_list = []
                for d in departments.split(','):
                    if d.strip().isdigit():
                        dept_list.append(int(d.strip()))
                
                if dept_list:  # Only update if at least one valid department ID
                    sync_service.DEPARTMENTS = dept_list
                    os.environ['DEPARTMENTS'] = departments  # Use correct environment variable name
                    logger.info(f"Departments updated to: {dept_list}")
                    
                    # Reiniciar la variable en sync_service directamente
                    if hasattr(sync_service, 'DEPARTMENTS'):
                        sync_service.DEPARTMENTS = dept_list
                        
                    flash('Los departamentos seleccionados han sido actualizados correctamente', 'success')
                else:
                    flash('No valid department IDs provided, using default departments', 'warning')
            except Exception as dept_e:
                flash(f'Error parsing departments: {str(dept_e)}', 'warning')
                logger.error(f"Error parsing departments: {str(dept_e)}")'''
        
        # Reemplazar el bloque
        if old_block in content:
            updated_content = content.replace(old_block, new_block)
            
            # Guardar archivo actualizado
            with open(app_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
                
            logger.info("Se actualizó la función save_settings en app.py")
        else:
            logger.warning("No se pudo encontrar el bloque de código en la función save_settings")
    
    except Exception as e:
        logger.error(f"Error al modificar app.py: {str(e)}")
        raise

def update_translations():
    """Agregar nueva traducción para el selector múltiple"""
    try:
        translations_path = 'd:\\HousingMaintenance\\HousingMaintenance-4\\translations.py'
        
        # Leer el archivo translations.py
        with open(translations_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Buscar la sección adecuada para añadir la nueva traducción
        en_section = "# Settings page"
        ar_section = "# Settings page"
        
        # Añadir la nueva traducción en inglés
        en_translation = "        'select_multiple_departments': 'Hold Ctrl/Cmd to select multiple departments',"
        ar_translation = "        'select_multiple_departments': 'اضغط Ctrl/Cmd لاختيار عدة أقسام',"
        
        # Encontrar la posición correcta para insertar las traducciones
        en_pos = content.find(en_section)
        ar_pos = content.find(ar_section, len(content) // 2)  # Buscar en la segunda mitad del archivo
        
        if en_pos >= 0 and ar_pos >= 0:
            # Encontrar el final de la línea para insertar después
            en_end = content.find('\n', en_pos) + 1
            ar_end = content.find('\n', ar_pos) + 1
            
            # Insertar las traducciones
            new_content = (
                content[:en_end + 10] + 
                en_translation + '\n        ' + 
                content[en_end + 10:ar_end + 10] + 
                ar_translation + '\n        ' + 
                content[ar_end + 10:]
            )
            
            # Guardar archivo actualizado
            with open(translations_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
                
            logger.info("Se actualizaron las traducciones en translations.py")
        else:
            logger.warning("No se encontraron las secciones correctas en translations.py")
    
    except Exception as e:
        logger.error(f"Error al modificar translations.py: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        logger.info("Iniciando mejoras en la selección de departamentos...")
        
        # Fix 1: Mejorar la carga de los departamentos en sync_service.py
        fix_departments_variable()
        
        # Fix 2: Actualizar el selector de departamentos en el template
        fix_departments_selector()
        
        # Fix 3: Actualizar la ruta settings para pasar los departamentos a la plantilla
        update_settings_route()
        
        # Fix 4: Actualizar la función save_settings para el nuevo selector
        update_save_settings_route()
        
        # Fix 5: Actualizar traducciones
        update_translations()
        
        logger.info("¡Mejoras completadas con éxito!")
        
        print("=== INSTRUCCIONES ===")
        print("1. Reinicie la aplicación para aplicar los cambios")
        print("2. Vaya a la página de configuración")
        print("3. Ahora podrá seleccionar múltiples departamentos de la lista")
        print("4. Los departamentos seleccionados se utilizarán correctamente en la sincronización")
        
    except Exception as e:
        logger.error(f"Error al aplicar las mejoras: {str(e)}")
        sys.exit(1)
