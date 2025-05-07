import sys
import io
import locale

def configure_terminal_for_arabic():
    """Configure terminal for proper Arabic text display"""
    # Try to set locale to Arabic
    try:
        # Try to set a UTF-8 Arabic locale if available
        locale.setlocale(locale.LC_ALL, 'ar_AE.UTF-8')  # United Arab Emirates Arabic
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'ar_SA.UTF-8')  # Saudi Arabia Arabic
        except locale.Error:
            try:
                # Fallback to any available locale with UTF-8
                locale.setlocale(locale.LC_ALL, '')
            except:
                pass
    
    # Ensure stdout/stderr use UTF-8
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def normalize_arabic_text(text):
    """
    Normalize Arabic text for better display compatibility
    Handles special characters and ensures proper encoding
    """
    if text is None:
        return ""
    
    # Replace problematic characters if needed
    replacements = {
        # Add specific replacements if needed
    }
    
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    
    return text

def print_arabic(text):
    """Print Arabic text to console with proper encoding"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback if terminal doesn't support Unicode
        encoded_text = text.encode('utf-8', errors='replace').decode('utf-8')
        print(f"(Encoded): {encoded_text}")
