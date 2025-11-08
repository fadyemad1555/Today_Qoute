import flet as ft
import os
import traceback
import urllib.request
import urllib.error
from datetime import datetime
import hashlib
from typing import Optional
import tempfile
import asyncio
import logging
from pathlib import Path
import sqlite3
import json

# Setup logging
LOG_DIR = Path(tempfile.gettempdir()) / "wallpaper_studio_logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"wallpaper_studio_{datetime.now().strftime('%Y%m%d')}.log"
DB_FILE = LOG_DIR / "wallpaper_studio_logs.db"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Platform detection
IS_ANDROID = False
try:
    import sys
    if 'ANDROID_APP_PATH' in os.environ or 'ANDROID_ROOT' in os.environ:
        IS_ANDROID = True
    elif sys.platform.startswith('linux') and os.path.exists('/system/build.prop'):
        IS_ANDROID = True
    logger.info(f"Platform: {'Android' if IS_ANDROID else 'Desktop'}")
except Exception as e:
    logger.error(f"Platform detection error: {e}")

class LogDatabase:
    """Database manager for logs"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    exception TEXT,
                    traceback TEXT,
                    platform TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_level ON logs(level)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_category ON logs(category)
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def add_log(self, level: str, category: str, message: str, 
                exception: Optional[Exception] = None):
        """Add a log entry to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exception_str = str(exception) if exception else None
            traceback_str = traceback.format_exc() if exception else None
            platform = "Android" if IS_ANDROID else "Desktop"
            
            cursor.execute('''
                INSERT INTO logs (timestamp, level, category, message, exception, traceback, platform)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, level, category, message, exception_str, traceback_str, platform))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to add log to database: {e}")
    
    def get_logs(self, limit: int = 100, level: Optional[str] = None,
                 category: Optional[str] = None) -> list:
        """Retrieve logs from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM logs WHERE 1=1"
            params = []
            
            if level:
                query += " AND level = ?"
                params.append(level)
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            conn.close()
            
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve logs: {e}")
            return []
    
    def get_statistics(self) -> dict:
        """Get log statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM logs")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT level, COUNT(*) FROM logs GROUP BY level")
            by_level = dict(cursor.fetchall())
            
            cursor.execute("SELECT category, COUNT(*) FROM logs GROUP BY category")
            by_category = dict(cursor.fetchall())
            
            cursor.execute("""
                SELECT COUNT(*) FROM logs 
                WHERE timestamp >= datetime('now', '-1 day')
            """)
            last_24h = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total,
                'by_level': by_level,
                'by_category': by_category,
                'last_24h': last_24h
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def clear_old_logs(self, days: int = 30):
        """Clear logs older than specified days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM logs 
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted {deleted} old log entries")
            return deleted
        except Exception as e:
            logger.error(f"Failed to clear old logs: {e}")
            return 0
    
    def export_logs(self, output_file: Path):
        """Export logs to JSON file"""
        try:
            logs = self.get_logs(limit=10000)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported {len(logs)} logs to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False

# Initialize database
log_db = LogDatabase(DB_FILE)

def log_error(level: str, category: str, message: str, 
              exception: Optional[Exception] = None) -> str:
    """Log errors with timestamp and save to database"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] [{category}] {message}"
    
    if exception:
        full_msg = f"{full_msg}\n{str(exception)}"
        logger.error(full_msg, exc_info=True)
    else:
        if level == "ERROR":
            logger.error(full_msg)
        elif level == "WARNING":
            logger.warning(full_msg)
        elif level == "INFO":
            logger.info(full_msg)
    
    # Save to database
    log_db.add_log(level, category, message, exception)
    
    return full_msg

def get_cache_path(url: str) -> str:
    """Generate cache path"""
    try:
        if IS_ANDROID:
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                context = PythonActivity.mActivity.getApplicationContext()
                cache_dir = str(context.getCacheDir().getAbsolutePath())
                logger.info(f"Android cache: {cache_dir}")
            except Exception as e:
                logger.warning(f"Android cache failed: {e}")
                cache_dir = os.path.join(tempfile.gettempdir(), 'wallpaper_cache')
        else:
            cache_dir = os.path.join(tempfile.gettempdir(), 'wallpaper_cache')
        
        os.makedirs(cache_dir, exist_ok=True)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(url.split('?')[0])[-1] or '.jpg'
        return os.path.join(cache_dir, f"{url_hash}{ext}")
    except Exception as e:
        log_error("ERROR", "CACHE", "Cache path generation failed", e)
        raise

async def download_image_async(url: str, dest_path: str, progress_callback=None) -> tuple[bool, str]:
    """Download image asynchronously"""
    log_error("INFO", "DOWNLOAD", f"Starting download: {url[:100]}")
    
    for attempt in range(3):
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                log_error("INFO", "DOWNLOAD", "Using cached image")
                return True, dest_path
            
            log_error("INFO", "DOWNLOAD", f"Attempt {attempt + 1}/3")
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'image/*')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content_type = response.headers.get('Content-Type', '')
                
                if not content_type.startswith('image/'):
                    return False, f"Invalid content: {content_type}"
                
                total_size = int(response.headers.get('Content-Length', 0))
                log_error("INFO", "DOWNLOAD", f"Size: {total_size / 1024:.1f} KB")
                
                data = bytearray()
                downloaded = 0
                
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    data.extend(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback and total_size:
                        await progress_callback(downloaded / total_size)
                
                if len(data) == 0:
                    return False, "Empty file"
                
                if len(data) > 50 * 1024 * 1024:
                    return False, f"Too large: {len(data) / (1024*1024):.1f}MB"
                
                temp_path = dest_path + '.tmp'
                with open(temp_path, 'wb') as f:
                    f.write(data)
                os.replace(temp_path, dest_path)
                
                log_error("INFO", "DOWNLOAD", f"Downloaded: {len(data) / 1024:.1f} KB")
                return True, dest_path
                
        except Exception as e:
            log_error("ERROR", "DOWNLOAD", f"Attempt {attempt + 1} failed", e)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            return False, str(e)[:100]
    
    return False, "Failed after 3 attempts"

def set_wallpaper_android(image_path: str) -> tuple[bool, str]:
    """Set wallpaper on Android"""
    log_error("INFO", "WALLPAPER", f"Setting wallpaper: {image_path}")
    
    try:
        if not IS_ANDROID:
            return False, "⚠️ Android only feature"
        
        if not os.path.exists(image_path):
            return False, "❌ File not found"
        
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        log_error("INFO", "WALLPAPER", f"File size: {file_size:.2f} MB")
        
        if file_size > 50 or file_size == 0:
            return False, f"❌ Invalid size: {file_size:.1f}MB"
        
        try:
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', currentActivity.getApplicationContext())
            
            File = autoclass('java.io.File')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            Options = autoclass('android.graphics.BitmapFactory$Options')
            
            file = File(image_path)
            options = Options()
            options.inJustDecodeBounds = True
            BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
            log_error("INFO", "WALLPAPER", f"Dimensions: {options.outWidth}x{options.outHeight}")
            
            if options.outWidth <= 0 or options.outHeight <= 0:
                return False, "❌ Invalid dimensions"
            
            max_dimension = 4096
            if options.outWidth > max_dimension or options.outHeight > max_dimension:
                scale = max(options.outWidth, options.outHeight) / max_dimension
                options.inSampleSize = int(scale)
                log_error("INFO", "WALLPAPER", f"Sampling: {options.inSampleSize}")
            
            options.inJustDecodeBounds = False
            bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
            if not bitmap:
                return False, "❌ Decode failed"
            
            WallpaperManager = autoclass('android.app.WallpaperManager')
            manager = WallpaperManager.getInstance(context)
            manager.setBitmap(bitmap)
            bitmap.recycle()
            
            log_error("INFO", "WALLPAPER", "Wallpaper set successfully")
            return True, "✅ Wallpaper set!"
            
        except ImportError:
            return False, "❌ Android libs unavailable"
        except Exception as e:
            log_error("ERROR", "WALLPAPER", "Android API error", e)
            return False, f"❌ Error: {str(e)[:100]}"
    except Exception as e:
        log_error("ERROR", "WALLPAPER", "Critical wallpaper error", e)
        return False, "❌ Critical error"

class WallpaperApp:
    """Main app class"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.selected_image: Optional[str] = None
        self.selected_container: Optional[ft.Container] = None
        self.is_loading = False
        self.read_permission_granted = False
        self.write_permission_granted = False
        
        log_error("INFO", "APP", "App initialized")
        
        # Import permission handler
        self.permission_handler = None
        self.has_permission_handler = False
        
        try:
            import flet_permission_handler as fph
            self.fph = fph
            self.permission_handler = fph.PermissionHandler()
            self.has_permission_handler = True
            log_error("INFO", "PERMISSION", "flet-permission-handler loaded successfully")
        except ImportError:
            log_error("WARNING", "PERMISSION", "flet-permission-handler not installed")
        
        self.status_text = ft.Text("", size=13, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
        self.status_icon = ft.Icon(ft.Icons.INFO_OUTLINE, size=18)
        self.loading_ring = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=3, color=ft.Colors.CYAN_400)
        self.progress_bar = ft.ProgressBar(visible=False, width=300, height=4, color=ft.Colors.CYAN_400, bgcolor=ft.Colors.GREY_800)
        
        self.images = [
            "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/2387418/pexels-photo-2387418.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/1252869/pexels-photo-1252869.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/1287145/pexels-photo-1287145.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/1591373/pexels-photo-1591373.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/1308940/pexels-photo-1308940.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/1761279/pexels-photo-1761279.jpeg?auto=compress&cs=tinysrgb&w=400",
            "https://images.pexels.com/photos/2662116/pexels-photo-2662116.jpeg?auto=compress&cs=tinysrgb&w=400",
        ]
        
        log_error("INFO", "APP", f"Loaded {len(self.images)} images")
    
    def show_snackbar(self, message: str, bgcolor: str = ft.Colors.BLUE_700):
        """Show snackbar"""
        try:
            icon = ft.Icons.CHECK_CIRCLE if "✅" in message else \
                   ft.Icons.ERROR if "❌" in message else \
                   ft.Icons.WARNING if "⚠️" in message else ft.Icons.INFO
            
            snack = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(icon, color=ft.Colors.WHITE, size=18),
                    ft.Text(message, color=ft.Colors.WHITE, size=14),
                ], spacing=10),
                bgcolor=bgcolor,
                duration=3000,
                behavior=ft.SnackBarBehavior.FLOATING,
            )
            self.page.overlay.append(snack)
            snack.open = True
            self.page.update()
        except Exception as e:
            log_error("ERROR", "UI", "Snackbar display error", e)
    
    async def check_permissions(self):
        """Check and request READ and WRITE permissions"""
        try:
            log_error("INFO", "PERMISSION", "=" * 50)
            log_error("INFO", "PERMISSION", "CHECKING PERMISSIONS")
            log_error("INFO", "PERMISSION", "=" * 50)
            
            if not IS_ANDROID:
                self.read_permission_granted = True
                self.write_permission_granted = True
                log_error("INFO", "PERMISSION", "Non-Android platform, permissions not required")
                return True
            
            if not self.has_permission_handler or not self.permission_handler:
                log_error("WARNING", "PERMISSION", "Permission handler not available, using basic check")
                return await self.check_permissions_basic()
            
            # Check and request READ_EXTERNAL_STORAGE permission
            read_granted = await self.check_single_permission(
                self.fph.PermissionType.STORAGE,
                "READ_EXTERNAL_STORAGE"
            )
            
            # Check and request WRITE_EXTERNAL_STORAGE permission
            write_granted = await self.check_single_permission(
                self.fph.PermissionType.STORAGE,
                "WRITE_EXTERNAL_STORAGE"
            )
            
            self.read_permission_granted = read_granted
            self.write_permission_granted = write_granted
            
            if read_granted and write_granted:
                self.show_snackbar("✅ All permissions granted", ft.Colors.GREEN_700)
                log_error("INFO", "PERMISSION", "All storage permissions granted")
                return True
            else:
                self.show_snackbar("⚠️ Some permissions denied", ft.Colors.ORANGE_700)
                log_error("WARNING", "PERMISSION", f"Permissions - Read: {read_granted}, Write: {write_granted}")
                return False
                
        except Exception as e:
            log_error("ERROR", "PERMISSION", "Permission check failed", e)
            self.read_permission_granted = True
            self.write_permission_granted = True
            return True
    
    
    async def check_permissions_basic(self):
        """Basic permission check without permission handler"""
        log_error("INFO", "PERMISSION", "Using basic permission check")
        try:
            test_file = os.path.join(tempfile.gettempdir(), 'wallpaper_test.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            self.read_permission_granted = True
            self.write_permission_granted = True
            log_error("INFO", "PERMISSION", "Storage write test successful")
            return True
        except Exception as e:
            log_error("WARNING", "PERMISSION", "Storage write test failed", e)
            self.show_snackbar("⚠️ Storage permission may be needed", ft.Colors.ORANGE_700)
            self.read_permission_granted = False
            self.write_permission_granted = False
            return False
    
    async def open_app_settings(self, e):
        """Open app settings"""
        try:
            log_error("INFO", "SETTINGS", "Opening app settings...")
            
            if self.has_permission_handler and self.permission_handler:
                success = await self.permission_handler.open_app_settings()
                if success:
                    log_error("INFO", "SETTINGS", "App settings opened")
                    self.show_snackbar("📱 Opening settings...", ft.Colors.BLUE_700)
                else:
                    log_error("WARNING", "SETTINGS", "Failed to open settings via permission handler")
                    self.show_snackbar("❌ Could not open settings", ft.Colors.RED_700)
            else:
                if IS_ANDROID:
                    try:
                        from jnius import autoclass
                        Intent = autoclass('android.content.Intent')
                        Settings = autoclass('android.provider.Settings')
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        Uri = autoclass('android.net.Uri')
                        
                        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                        package_name = PythonActivity.mActivity.getPackageName()
                        intent.setData(Uri.parse(f"package:{package_name}"))
                        PythonActivity.mActivity.startActivity(intent)
                        
                        log_error("INFO", "SETTINGS", "App settings opened (Android API)")
                        self.show_snackbar("📱 Opening settings...", ft.Colors.BLUE_700)
                    except Exception as android_error:
                        log_error("ERROR", "SETTINGS", "Android settings error", android_error)
                        self.show_snackbar("❌ Could not open settings", ft.Colors.RED_700)
                else:
                    self.show_snackbar("⚠️ Settings not available on this platform", ft.Colors.ORANGE_700)
                    
        except Exception as e:
            log_error("ERROR", "SETTINGS", "Failed to open settings", e)
            self.show_snackbar("❌ Could not open settings", ft.Colors.RED_700)
    
    def show_status(self, message: str, color: str, icon: str = ft.Icons.INFO_OUTLINE):
        """Update status"""
        try:
            self.status_text.value = message
            self.status_text.color = color
            self.status_icon.name = icon
            self.status_icon.color = color
            self.page.update()
        except Exception as e:
            log_error("ERROR", "UI", "Status update error", e)
    
    def show_loading(self, loading: bool):
        """Toggle loading"""
        self.is_loading = loading
        self.loading_ring.visible = loading
        self.page.update()
    
    def show_progress(self, visible: bool, value: float = 0.0):
        """Update progress"""
        self.progress_bar.visible = visible
        if visible:
            self.progress_bar.value = value
        self.page.update()
    
    def show_log_viewer(self, e):
        """Show database log viewer"""
        try:
            stats = log_db.get_statistics()
            logs = log_db.get_logs(limit=50)
            
            def close_dlg(e):
                dlg.open = False
                self.page.update()
            
            def refresh_logs(e):
                nonlocal logs
                filter_level = level_dropdown.value if level_dropdown.value != "ALL" else None
                filter_category = category_dropdown.value if category_dropdown.value != "ALL" else None
                logs = log_db.get_logs(limit=50, level=filter_level, category=filter_category)
                update_log_list()
            
            def clear_old_logs(e):
                deleted = log_db.clear_old_logs(days=30)
                self.show_snackbar(f"✅ Deleted {deleted} old logs", ft.Colors.GREEN_700)
                refresh_logs(e)
            
            def export_logs(e):
                export_file = LOG_DIR / f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                if log_db.export_logs(export_file):
                    self.show_snackbar(f"✅ Exported to {export_file.name}", ft.Colors.GREEN_700)
                else:
                    self.show_snackbar("❌ Export failed", ft.Colors.RED_700)
            
            # Create filter dropdowns
            level_dropdown = ft.Dropdown(
                width=120,
                value="ALL",
                options=[
                    ft.dropdown.Option("ALL"),
                    ft.dropdown.Option("INFO"),
                    ft.dropdown.Option("WARNING"),
                    ft.dropdown.Option("ERROR"),
                ],
                on_change=refresh_logs,
            )
            
            category_dropdown = ft.Dropdown(
                width=150,
                value="ALL",
                options=[
                    ft.dropdown.Option("ALL"),
                    ft.dropdown.Option("APP"),
                    ft.dropdown.Option("PERMISSION"),
                    ft.dropdown.Option("DOWNLOAD"),
                    ft.dropdown.Option("WALLPAPER"),
                    ft.dropdown.Option("UI"),
                    ft.dropdown.Option("CACHE"),
                    ft.dropdown.Option("SETTINGS"),
                ],
                on_change=refresh_logs,
            )
            
            log_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=300)
            
            def update_log_list():
                log_list.controls.clear()
                for log in logs:
                    level_color = {
                        'ERROR': ft.Colors.RED_400,
                        'WARNING': ft.Colors.ORANGE_400,
                        'INFO': ft.Colors.CYAN_400,
                    }.get(log['level'], ft.Colors.GREY_400)
                    
                    log_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(
                                        ft.Icons.ERROR if log['level'] == 'ERROR' else
                                        ft.Icons.WARNING if log['level'] == 'WARNING' else
                                        ft.Icons.INFO,
                                        size=16,
                                        color=level_color
                                    ),
                                    ft.Text(log['timestamp'], size=10, color=ft.Colors.GREY_500),
                                    ft.Container(
                                        content=ft.Text(log['level'], size=10, weight=ft.FontWeight.BOLD),
                                        bgcolor=level_color,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=4,
                                    ),
                                    ft.Container(
                                        content=ft.Text(log['category'], size=10),
                                        bgcolor=ft.Colors.GREY_700,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=4,
                                    ),
                                ], spacing=8),
                                ft.Text(log['message'], size=11, color=ft.Colors.WHITE, selectable=True),
                                ft.Text(log['exception'][:200] if log['exception'] else "", size=9, color=ft.Colors.RED_300, selectable=True) if log['exception'] else ft.Container(),
                            ], spacing=4),
                            padding=10,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=8,
                            border=ft.border.all(1, ft.Colors.GREY_800),
                        )
                    )
                self.page.update()
            
            update_log_list()
            
            # Statistics display
            stats_display = ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.ANALYTICS, size=16, color=ft.Colors.CYAN_400),
                    ft.Text("Statistics", size=14, weight=ft.FontWeight.BOLD),
                ], spacing=8),
                ft.Row([
                    ft.Text(f"Total: {stats.get('total', 0)}", size=11),
                    ft.Text(f"Last 24h: {stats.get('last_24h', 0)}", size=11),
                ], spacing=20),
                ft.Row([
                    ft.Text(f"Errors: {stats.get('by_level', {}).get('ERROR', 0)}", size=11, color=ft.Colors.RED_400),
                    ft.Text(f"Warnings: {stats.get('by_level', {}).get('WARNING', 0)}", size=11, color=ft.Colors.ORANGE_400),
                    ft.Text(f"Info: {stats.get('by_level', {}).get('INFO', 0)}", size=11, color=ft.Colors.CYAN_400),
                ], spacing=15),
            ], spacing=8)
            
            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.DATA_OBJECT, color=ft.Colors.CYAN_400, size=24),
                    ft.Text("Database Logs", weight=ft.FontWeight.BOLD, size=18),
                ], spacing=10),
                content=ft.Container(
                    content=ft.Column([
                        stats_display,
                        ft.Divider(height=1),
                        ft.Row([
                            ft.Text("Filters:", size=12, weight=ft.FontWeight.BOLD),
                            level_dropdown,
                            category_dropdown,
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                tooltip="Refresh",
                                on_click=refresh_logs,
                            ),
                        ], spacing=10),
                        ft.Text(f"Showing {len(logs)} most recent logs:", size=12, color=ft.Colors.GREY_400),
                        log_list,
                    ], spacing=8),
                    width=600,
                ),
                actions=[
                    ft.TextButton("Export JSON", icon=ft.Icons.DOWNLOAD, on_click=export_logs),
                    ft.TextButton("Clear Old", icon=ft.Icons.DELETE_SWEEP, on_click=clear_old_logs),
                    ft.TextButton("Close", on_click=close_dlg),
                ],
            )
            
            self.page.open(dlg)
            
        except Exception as e:
            log_error("ERROR", "UI", "Failed to show log viewer", e)
            self.show_snackbar("❌ Could not open log viewer", ft.Colors.RED_700)
    
    def on_image_click(self, e, img_path: str, container: ft.Container):
        """Handle selection"""
        try:
            log_error("INFO", "UI", f"Image selected: {img_path[:50]}...")
            
            if self.selected_container:
                self.selected_container.border = ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE))
                self.selected_container.shadow = None
            
            self.selected_image = img_path
            self.selected_container = container
            
            container.border = ft.border.all(3, ft.Colors.CYAN_400)
            container.shadow = ft.BoxShadow(
                spread_radius=2,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.8, ft.Colors.CYAN_400),
                offset=ft.Offset(0, 4),
            )
            
            self.show_snackbar("✓ Selected", ft.Colors.CYAN_700)
            self.show_status("Ready", ft.Colors.CYAN_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
            self.page.update()
            
        except Exception as e:
            log_error("ERROR", "UI", "Selection error", e)
            self.show_snackbar("❌ Error", ft.Colors.RED_700)
    
    def clear_selection(self, e):
        """Clear selection"""
        try:
            if self.selected_container:
                self.selected_container.border = ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE))
                self.selected_container.shadow = None
            
            self.selected_image = None
            self.selected_container = None
            self.status_text.value = ""
            self.show_snackbar("Cleared", ft.Colors.GREY_700)
            log_error("INFO", "UI", "Selection cleared")
            self.page.update()
        except Exception as e:
            log_error("ERROR", "UI", "Clear selection error", e)
    
    def set_wallpaper_click(self, e):
        """Handle wallpaper button click - wrapper for async function"""
        try:
            log_error("INFO", "WALLPAPER", "Set wallpaper button clicked")
            self.page.run_task(self.set_wallpaper_async)
        except Exception as e:
            log_error("ERROR", "WALLPAPER", "Failed to start wallpaper task", e)
            self.show_snackbar("❌ Failed to start", ft.Colors.RED_700)
    
    async def set_wallpaper_async(self):
        """Set wallpaper"""
        try:
            if self.is_loading:
                self.show_snackbar("⏳ Wait", ft.Colors.ORANGE_700)
                return
            
            if not self.selected_image:
                self.show_snackbar("⚠️ Select image", ft.Colors.ORANGE_700)
                return
            
            log_error("INFO", "WALLPAPER", "=" * 50)
            log_error("INFO", "WALLPAPER", f"Setting wallpaper: {self.selected_image}")
            
            # Check permissions first
            if IS_ANDROID and not (self.read_permission_granted and self.write_permission_granted):
                self.show_status("Checking permissions...", ft.Colors.CYAN_400, ft.Icons.SECURITY)
                has_perm = await self.check_permissions()
                
                if not has_perm:
                    log_error("WARNING", "PERMISSION", "Permissions denied, showing dialog")
                    self.show_permission_dialog()
                    return
            
            self.show_loading(True)
            self.show_status("Processing...", ft.Colors.CYAN_400, ft.Icons.SYNC)
            
            img_path = self.selected_image
            
            # Download if URL
            if img_path.startswith('http'):
                self.show_status("Downloading...", ft.Colors.CYAN_400, ft.Icons.DOWNLOAD)
                self.show_progress(True, 0.0)
                
                try:
                    cache_path = get_cache_path(img_path)
                    
                    async def update_progress(progress):
                        try:
                            self.show_progress(True, progress)
                        except Exception as pe:
                            log_error("ERROR", "UI", "Progress update error", pe)
                    
                    success, result = await download_image_async(img_path, cache_path, update_progress)
                    
                    self.show_progress(False)
                    
                    if not success:
                        self.show_loading(False)
                        self.show_status("Failed", ft.Colors.RED_400, ft.Icons.ERROR)
                        self.show_snackbar(f"❌ Download failed: {result}", ft.Colors.RED_700)
                        log_error("ERROR", "DOWNLOAD", f"Download failed: {result}")
                        return
                    
                    img_path = result
                    self.show_status("Downloaded", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                    log_error("INFO", "DOWNLOAD", f"Download successful: {img_path}")
                    
                except Exception as download_error:
                    self.show_loading(False)
                    self.show_progress(False)
                    log_error("ERROR", "DOWNLOAD", "Download exception", download_error)
                    self.show_snackbar("❌ Download error", ft.Colors.RED_700)
                    return
            
            # Set wallpaper
            self.show_status("Setting...", ft.Colors.CYAN_400, ft.Icons.WALLPAPER)
            
            try:
                success, message = set_wallpaper_android(img_path)
                
                self.show_loading(False)
                
                if success:
                    self.show_status("Success!", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                    self.show_snackbar(message, ft.Colors.GREEN_700)
                    log_error("INFO", "WALLPAPER", "Wallpaper set successfully")
                else:
                    self.show_status("Failed", ft.Colors.ORANGE_400, ft.Icons.WARNING)
                    self.show_snackbar(message, ft.Colors.ORANGE_700)
                    log_error("ERROR", "WALLPAPER", f"Failed to set wallpaper: {message}")
                    
            except Exception as wallpaper_error:
                self.show_loading(False)
                log_error("ERROR", "WALLPAPER", "Wallpaper setting exception", wallpaper_error)
                self.show_snackbar("❌ Wallpaper error", ft.Colors.RED_700)
                self.show_status("Error", ft.Colors.RED_400, ft.Icons.ERROR)
            
            log_error("INFO", "WALLPAPER", "=" * 50)
            
        except Exception as e:
            self.show_loading(False)
            self.show_progress(False)
            log_error("ERROR", "WALLPAPER", "Critical wallpaper operation error", e)
            self.show_status("Error", ft.Colors.RED_400, ft.Icons.ERROR)
            self.show_snackbar("❌ Critical error", ft.Colors.RED_700)
    
    def show_permission_dialog(self):
        """Show permission dialog"""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        async def open_settings_and_close(e):
            await self.open_app_settings(e)
            await asyncio.sleep(0.5)
            close_dlg(e)
        
        permission_status = []
        if not self.read_permission_granted:
            permission_status.append("❌ Read External Storage")
        else:
            permission_status.append("✅ Read External Storage")
        
        if not self.write_permission_granted:
            permission_status.append("❌ Write External Storage")
        else:
            permission_status.append("✅ Write External Storage")
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.LOCK_OUTLINE, color=ft.Colors.ORANGE_400, size=28),
                ft.Text("Storage Permission Required", weight=ft.FontWeight.BOLD, size=18),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Wallpaper Studio needs storage permissions:", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=8),
                    ft.Row([ft.Icon(ft.Icons.DOWNLOAD, size=20, color=ft.Colors.CYAN_400), ft.Text("Download wallpaper images", size=13)], spacing=10),
                    ft.Row([ft.Icon(ft.Icons.SAVE, size=20, color=ft.Colors.CYAN_400), ft.Text("Cache images for faster access", size=13)], spacing=10),
                    ft.Row([ft.Icon(ft.Icons.WALLPAPER, size=20, color=ft.Colors.CYAN_400), ft.Text("Set wallpapers on your device", size=13)], spacing=10),
                    ft.Container(height=12),
                    ft.Text("Permission Status:", size=13, weight=ft.FontWeight.BOLD),
                    *[ft.Text(status, size=12) for status in permission_status],
                    ft.Container(height=8),
                    ft.Text(
                        "Click 'Open Settings' to enable required permissions.",
                        size=12,
                        color=ft.Colors.GREY_400,
                        italic=True,
                    ),
                ], spacing=8),
                padding=10,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.FilledButton("Open Settings", icon=ft.Icons.SETTINGS, on_click=open_settings_and_close),
            ],
        )
        
        self.page.open(dlg)
    
    def on_hover(self, e: ft.HoverEvent, container: ft.Container):
        """Hover effect"""
        try:
            if container == self.selected_container:
                return
            
            container.scale = 1.05 if e.data == "true" else 1.0
            container.shadow = ft.BoxShadow(
                spread_radius=1,
                blur_radius=12,
                color=ft.Colors.with_opacity(0.5, ft.Colors.CYAN_300),
                offset=ft.Offset(0, 3),
            ) if e.data == "true" else None
            
            self.page.update()
        except Exception as e:
            log_error("ERROR", "UI", "Hover effect error", e)
    
    def create_image_card(self, img_url: str) -> ft.Container:
        """Create image card"""
        img = ft.Image(
            src=img_url,
            fit=ft.ImageFit.COVER,
            width=165,
            height=165,
            border_radius=12,
            error_content=ft.Container(
                content=ft.Icon(ft.Icons.BROKEN_IMAGE, size=40, color=ft.Colors.GREY_600),
                width=165,
                height=165,
                bgcolor=ft.Colors.GREY_900,
                border_radius=12,
                alignment=ft.alignment.center,
            ),
        )
        
        container = ft.Container(
            content=img,
            width=165,
            height=165,
            border=ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            ink=True,
        )
        
        container.on_click = lambda e, path=img_url, cont=container: self.on_image_click(e, path, cont)
        container.on_hover = lambda e, cont=container: self.on_hover(e, cont)
        
        return container
    
    def create_image_grid(self) -> ft.Column:
        """Create grid"""
        rows = []
        row_items = []
        
        for i, img in enumerate(self.images):
            card = self.create_image_card(img)
            row_items.append(card)
            
            if (i + 1) % 2 == 0:
                rows.append(ft.Row(row_items, spacing=15, alignment=ft.MainAxisAlignment.CENTER))
                row_items = []
        
        if row_items:
            rows.append(ft.Row(row_items, spacing=15, alignment=ft.MainAxisAlignment.CENTER))
        
        return ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PHOTO_LIBRARY, size=16, color=ft.Colors.WHITE),
                    ft.Text(f"{len(self.images)} wallpapers", size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                bgcolor=ft.Colors.CYAN_700,
                border_radius=20,
            ),
            ft.Container(height=16),
            *rows,
            ft.Container(height=140),
        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    def build(self) -> ft.Control:
        """Build UI"""
        
        # Add permission handler to overlay if available
        if self.permission_handler:
            self.page.overlay.append(self.permission_handler)
            log_error("INFO", "APP", "Permission handler added to page overlay")
        
        header = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.WALLPAPER_ROUNDED, size=32, color=ft.Colors.CYAN_400),
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.CYAN_400),
                    border_radius=12,
                    padding=8,
                ),
                ft.Column([
                    ft.Text("Wallpaper Studio", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text("Transform your screen", size=12, color=ft.Colors.GREY_400),
                ], spacing=2, expand=True),
            ], spacing=12),
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#0f172a", "#1e293b"],
            ),
        )
        
        bottom = ft.Container(
            content=ft.Column([
                ft.Row([self.status_icon, self.status_text], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                self.progress_bar,
                ft.Row([
                    ft.IconButton(icon=ft.Icons.CLEAR, tooltip="Clear Selection", icon_size=24, on_click=self.clear_selection, bgcolor=ft.Colors.GREY_800),
                    ft.Container(
                        content=ft.Row([
                            self.loading_ring,
                            ft.Icon(ft.Icons.WALLPAPER, size=20),
                            ft.Text("Set Wallpaper", size=15, weight=ft.FontWeight.BOLD),
                        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                        padding=16,
                        bgcolor=ft.Colors.CYAN_700,
                        border_radius=12,
                        ink=True,
                        on_click=self.set_wallpaper_click,
                        expand=True,
                    ),
                    ft.IconButton(icon=ft.Icons.DATA_OBJECT, tooltip="Database Logs", icon_size=24, on_click=self.show_log_viewer, bgcolor=ft.Colors.GREY_800),
                ], spacing=10),
            ], spacing=10),
            padding=16,
            bgcolor=ft.Colors.with_opacity(0.95, "#1a1f2e"),
        )
        
        return ft.Stack([
            ft.Column([
                header,
                ft.Container(
                    content=ft.ListView([self.create_image_grid()], padding=20),
                    expand=True,
                ),
            ], spacing=0, expand=True),
            ft.Container(content=bottom, alignment=ft.alignment.bottom_center),
        ], expand=True)

def main(page: ft.Page):
    """Main entry"""
    try:
        log_error("INFO", "APP", "Starting Wallpaper Studio application")
        
        page.title = "Wallpaper Studio"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.bgcolor = "#0a0e1a"
        page.scroll = ft.ScrollMode.HIDDEN
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.CYAN, use_material3=True)
        
        app = WallpaperApp(page)
        page.add(app.build())
        
        app.show_status(f"Ready • {len(app.images)} images", ft.Colors.GREY_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
        
        async def check_on_start():
            await asyncio.sleep(0.5)
            if IS_ANDROID:
                app.show_status("Checking permissions...", ft.Colors.CYAN_400, ft.Icons.SECURITY)
                await app.check_permissions()
                app.show_status(f"Ready • {len(app.images)} images", ft.Colors.GREY_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
        
        page.run_task(check_on_start)
        
        log_error("INFO", "APP", f"App started | Platform: {'Android' if IS_ANDROID else 'Desktop'} | Images: {len(app.images)}")
        log_error("INFO", "APP", f"Permission handler: {'Loaded' if app.has_permission_handler else 'Not available'}")
        log_error("INFO", "APP", f"Log file: {LOG_FILE}")
        log_error("INFO", "APP", f"Database: {DB_FILE}")
        
    except Exception as e:
        log_error("ERROR", "APP", "Fatal error in main", e)
        
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, size=60, color=ft.Colors.RED_400),
                    ft.Text("App Failed to Start", size=20, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e)[:150], size=11, color=ft.Colors.GREY_400, selectable=True, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Text(f"Log: {LOG_FILE}", size=10, color=ft.Colors.GREY_500, selectable=True),
                    ft.Text(f"DB: {DB_FILE}", size=10, color=ft.Colors.GREY_500, selectable=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                padding=40,
                expand=True,
                alignment=ft.alignment.center,
            )
        )

if __name__ == "__main__":
    try:
        log_error("INFO", "APP", "=" * 60)
        log_error("INFO", "APP", "WALLPAPER STUDIO - Starting Application")
        log_error("INFO", "APP", "=" * 60)
        ft.app(target=main)
    except Exception as e:
        log_error("ERROR", "APP", "Fatal startup error", e)
        print("\n" + "=" * 60)
        print("❌ APPLICATION FAILED TO START")
        print("=" * 60)
        print(f"\n{str(e)}")
        print(traceback.format_exc())
        print(f"\n📄 Log file: {LOG_FILE}")
        print(f"📄 Database: {DB_FILE}")
        print("=" * 60)