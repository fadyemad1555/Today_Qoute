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

# Setup logging
LOG_DIR = Path(tempfile.gettempdir()) / "wallpaper_studio_logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"wallpaper_studio_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

error_log = []

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

def log_error(error_msg: str, exception: Optional[Exception] = None) -> str:
    """Log errors with timestamp and traceback"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {error_msg}"
    
    if exception:
        full_msg = f"{full_msg}\n{str(exception)}\n{traceback.format_exc()}"
        logger.error(full_msg, exc_info=True)
    else:
        logger.error(full_msg)
    
    error_log.append(full_msg)
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
        log_error("Cache path error", e)
        raise

async def download_image_async(url: str, dest_path: str, progress_callback=None) -> tuple[bool, str]:
    """Download image asynchronously"""
    logger.info(f"Downloading: {url}")
    
    for attempt in range(3):
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                logger.info("Using cached image")
                return True, dest_path
            
            logger.info(f"Attempt {attempt + 1}/3")
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            req.add_header('Accept', 'image/*')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content_type = response.headers.get('Content-Type', '')
                
                if not content_type.startswith('image/'):
                    return False, f"Invalid content: {content_type}"
                
                total_size = int(response.headers.get('Content-Length', 0))
                logger.info(f"Size: {total_size / 1024:.1f} KB")
                
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
                
                logger.info(f"Downloaded: {len(data) / 1024:.1f} KB")
                return True, dest_path
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            return False, str(e)[:100]
    
    return False, "Failed after 3 attempts"

def set_wallpaper_android(image_path: str) -> tuple[bool, str]:
    """Set wallpaper on Android"""
    logger.info(f"Setting wallpaper: {image_path}")
    
    try:
        if not IS_ANDROID:
            return False, "⚠️ Android only feature"
        
        if not os.path.exists(image_path):
            return False, "❌ File not found"
        
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        logger.info(f"File size: {file_size:.2f} MB")
        
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
            
            logger.info(f"Dimensions: {options.outWidth}x{options.outHeight}")
            
            if options.outWidth <= 0 or options.outHeight <= 0:
                return False, "❌ Invalid dimensions"
            
            max_dimension = 4096
            if options.outWidth > max_dimension or options.outHeight > max_dimension:
                scale = max(options.outWidth, options.outHeight) / max_dimension
                options.inSampleSize = int(scale)
                logger.info(f"Sampling: {options.inSampleSize}")
            
            options.inJustDecodeBounds = False
            bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
            if not bitmap:
                return False, "❌ Decode failed"
            
            WallpaperManager = autoclass('android.app.WallpaperManager')
            manager = WallpaperManager.getInstance(context)
            manager.setBitmap(bitmap)
            bitmap.recycle()
            
            logger.info("Wallpaper set successfully")
            return True, "✅ Wallpaper set!"
            
        except ImportError:
            return False, "❌ Android libs unavailable"
        except Exception as e:
            log_error("Android API error", e)
            return False, f"❌ Error: {str(e)[:100]}"
    except Exception as e:
        log_error("Wallpaper error", e)
        return False, "❌ Critical error"

class WallpaperApp:
    """Main app class"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.selected_image: Optional[str] = None
        self.selected_container: Optional[ft.Container] = None
        self.is_loading = False
        self.storage_permission_granted = False
        
        logger.info("App initialized")
        
        # Try to import the new permission handler package
        self.permission_handler = None
        self.has_permission_handler = False
        
        try:
            import flet_permission_handler 
            self.permission_handler = flet_permission_handler.PermissionHandler()
            self.has_permission_handler = True
            logger.info("✓ flet-permission-handler loaded")
        except ImportError:
            logger.warning("⚠ flet-permission-handler not installed. Install with: pip install flet-permission-handler")
        
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
        
        logger.info(f"Loaded {len(self.images)} images")
    
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
            logger.error(f"Snackbar error: {e}")
    
    async def check_permissions(self):
        """Check and request permissions using flet-permission-handler"""
        try:
            logger.info("=" * 50)
            logger.info("CHECKING PERMISSIONS")
            logger.info("=" * 50)
            
            if not IS_ANDROID:
                self.storage_permission_granted = True
                logger.info("✓ Non-Android platform, permissions not required")
                return True
            
            # If permission handler is not available, do basic check
            if not self.has_permission_handler or not self.permission_handler:
                logger.warning("Permission handler not available, using basic check")
                return await self.check_permissions_basic()
            
            # Use the new permission handler
            try:
                # Check current storage permission status
                logger.info("Checking STORAGE permission status...")
                status = await self.permission_handler.check_permission(ft.PermissionType.STORAGE)
                logger.info(f"Storage permission status: {status}")
                
                if status == ft.PermissionStatus.GRANTED:
                    self.storage_permission_granted = True
                    logger.info("✓ Storage permission already granted")
                    self.show_snackbar("✅ Storage permission granted", ft.Colors.GREEN_700)
                    return True
                
                elif status == ft.PermissionStatus.DENIED:
                    # Permission denied but can be requested
                    logger.info("Storage permission denied, requesting...")
                    self.show_snackbar("📋 Requesting storage permission...", ft.Colors.BLUE_700)
                    
                    # Request permission
                    result = await self.permission_handler.request_permission(ft.PermissionType.STORAGE)
                    logger.info(f"Permission request result: {result}")
                    
                    if result == ft.PermissionStatus.GRANTED:
                        self.storage_permission_granted = True
                        logger.info("✓ Storage permission granted by user")
                        self.show_snackbar("✅ Permission granted!", ft.Colors.GREEN_700)
                        return True
                    else:
                        self.storage_permission_granted = False
                        logger.warning("✗ Storage permission denied by user")
                        self.show_snackbar("⚠️ Storage permission denied", ft.Colors.ORANGE_700)
                        return False
                
                elif status == ft.PermissionStatus.PERMANENTLY_DENIED:
                    # Permission permanently denied, need to open settings
                    logger.warning("Storage permission permanently denied")
                    self.storage_permission_granted = False
                    self.show_snackbar("⚠️ Permission denied. Open settings to enable.", ft.Colors.RED_700)
                    return False
                
                elif status == ft.PermissionStatus.LIMITED:
                    # Limited access (iOS only, but handle gracefully)
                    logger.info("Limited storage access granted")
                    self.storage_permission_granted = True
                    return True
                
                else:
                    # Unknown status
                    logger.warning(f"Unknown permission status: {status}")
                    return await self.check_permissions_basic()
                    
            except Exception as e:
                log_error("Permission handler error", e)
                logger.info("Falling back to basic permission check")
                return await self.check_permissions_basic()
                
        except Exception as e:
            log_error("Permission check failed", e)
            # Assume granted if check fails
            self.storage_permission_granted = True
            return True
    
    async def check_permissions_basic(self):
        """Basic permission check without permission handler"""
        logger.info("Using basic permission check")
        try:
            test_file = os.path.join(tempfile.gettempdir(), 'wallpaper_test.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            self.storage_permission_granted = True
            logger.info("✓ Storage write test successful")
            return True
        except Exception as e:
            logger.warning(f"✗ Storage write test failed: {e}")
            self.show_snackbar("⚠️ Storage permission may be needed", ft.Colors.ORANGE_700)
            self.storage_permission_granted = False
            return False
    
    async def open_app_settings(self, e):
        """Open app settings"""
        try:
            logger.info("Opening app settings...")
            
            if self.has_permission_handler and self.permission_handler:
                # Use permission handler to open settings
                success = await self.permission_handler.open_app_settings()
                if success:
                    logger.info("✓ App settings opened")
                    self.show_snackbar("📱 Opening settings...", ft.Colors.BLUE_700)
                else:
                    logger.warning("Failed to open settings via permission handler")
                    self.show_snackbar("❌ Could not open settings", ft.Colors.RED_700)
            else:
                # Fallback for Android without permission handler
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
                        
                        logger.info("✓ App settings opened (Android API)")
                        self.show_snackbar("📱 Opening settings...", ft.Colors.BLUE_700)
                    except Exception as android_error:
                        logger.error(f"Android settings error: {android_error}")
                        self.show_snackbar("❌ Could not open settings", ft.Colors.RED_700)
                else:
                    self.show_snackbar("⚠️ Settings not available on this platform", ft.Colors.ORANGE_700)
                    
        except Exception as e:
            log_error("Failed to open settings", e)
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
            logger.error(f"Status error: {e}")
    
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
    
    def show_error_dialog(self, e):
        """Show error log"""
        if not error_log:
            self.show_snackbar("✓ No errors", ft.Colors.GREEN_700)
            return
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        def clear_log(e):
            error_log.clear()
            close_dlg(e)
            self.show_snackbar("✓ Log cleared", ft.Colors.GREEN_700)
        
        def open_log_file(e):
            try:
                import subprocess
                if os.name == 'nt':
                    os.startfile(LOG_FILE)
                elif os.name == 'posix':
                    subprocess.run(['xdg-open', str(LOG_FILE)])
                logger.info(f"Opened: {LOG_FILE}")
            except Exception as ex:
                logger.error(f"Failed to open log: {ex}")
                self.show_snackbar("❌ Could not open log", ft.Colors.RED_700)
        
        errors = [
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Error {len(error_log) - i}", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                    ft.Text(error[:300] + "..." if len(error) > 300 else error, size=10, selectable=True, color=ft.Colors.GREY_300),
                ], spacing=4),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
            )
            for i, error in enumerate(reversed(error_log[-10:]))
        ]
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.BUG_REPORT, color=ft.Colors.ORANGE_400, size=24),
                ft.Text("Error Log", weight=ft.FontWeight.BOLD, size=18),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Log: {LOG_FILE}", size=10, color=ft.Colors.GREY_500, selectable=True),
                    ft.Divider(height=1),
                    *errors
                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                height=400,
                width=500,
            ),
            actions=[
                ft.TextButton("Open File", icon=ft.Icons.FOLDER_OPEN, on_click=open_log_file),
                ft.TextButton("Clear", icon=ft.Icons.DELETE_SWEEP, on_click=clear_log),
                ft.TextButton("Close", on_click=close_dlg),
            ],
        )
        
        self.page.open(dlg)
    
    def on_image_click(self, e, img_path: str, container: ft.Container):
        """Handle selection"""
        try:
            logger.info(f"Selected: {img_path[:50]}...")
            
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
            log_error("Selection error", e)
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
            self.page.update()
        except Exception as e:
            log_error("Clear error", e)
    
    async def set_wallpaper_async(self, e):
        """Set wallpaper"""
        try:
            if self.is_loading:
                self.show_snackbar("⏳ Wait", ft.Colors.ORANGE_700)
                return
            
            if not self.selected_image:
                self.show_snackbar("⚠️ Select image", ft.Colors.ORANGE_700)
                return
            
            logger.info("=" * 50)
            logger.info(f"Setting: {self.selected_image}")
            
            if not self.storage_permission_granted:
                self.show_status("Checking permissions...", ft.Colors.CYAN_400, ft.Icons.SECURITY)
                has_perm = await self.check_permissions()
                
                if not has_perm:
                    logger.warning("Permission denied, showing dialog")
                    self.show_permission_dialog()
                    return
            
            self.show_loading(True)
            self.show_status("Processing...", ft.Colors.CYAN_400, ft.Icons.SYNC)
            
            img_path = self.selected_image
            
            if img_path.startswith('http'):
                self.show_status("Downloading...", ft.Colors.CYAN_400, ft.Icons.DOWNLOAD)
                self.show_progress(True, 0.0)
                cache_path = get_cache_path(img_path)
                
                async def update_progress(progress):
                    self.show_progress(True, progress)
                
                success, result = await download_image_async(img_path, cache_path, update_progress)
                
                self.show_progress(False)
                
                if not success:
                    self.show_loading(False)
                    self.show_status("Failed", ft.Colors.RED_400, ft.Icons.ERROR)
                    self.show_snackbar(f"❌ {result}", ft.Colors.RED_700)
                    return
                
                img_path = result
                self.show_status("Downloaded", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
            
            self.show_status("Setting...", ft.Colors.CYAN_400, ft.Icons.WALLPAPER)
            success, message = set_wallpaper_android(img_path)
            
            self.show_loading(False)
            
            if success:
                self.show_status("Success!", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                self.show_snackbar(message, ft.Colors.GREEN_700)
            else:
                self.show_status("Failed", ft.Colors.ORANGE_400, ft.Icons.WARNING)
                self.show_snackbar(message, ft.Colors.ORANGE_700)
            
            logger.info("=" * 50)
            
        except Exception as e:
            self.show_loading(False)
            self.show_progress(False)
            log_error("Wallpaper error", e)
            self.show_status("Error", ft.Colors.RED_400, ft.Icons.ERROR)
            self.show_snackbar("❌ Error", ft.Colors.RED_700)
    
    def show_permission_dialog(self):
        """Show permission dialog"""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        async def open_settings_and_close(e):
            await self.open_app_settings(e)
            await asyncio.sleep(0.5)
            close_dlg(e)
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.LOCK_OUTLINE, color=ft.Colors.ORANGE_400, size=28),
                ft.Text("Storage Permission Required", weight=ft.FontWeight.BOLD, size=18),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Wallpaper Studio needs storage permission to:", size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=8),
                    ft.Row([ft.Icon(ft.Icons.DOWNLOAD, size=20, color=ft.Colors.CYAN_400), ft.Text("Download wallpaper images", size=13)], spacing=10),
                    ft.Row([ft.Icon(ft.Icons.SAVE, size=20, color=ft.Colors.CYAN_400), ft.Text("Cache images for faster access", size=13)], spacing=10),
                    ft.Row([ft.Icon(ft.Icons.WALLPAPER, size=20, color=ft.Colors.CYAN_400), ft.Text("Set wallpapers on your device", size=13)], spacing=10),
                    ft.Container(height=12),
                    ft.Text(
                        "Please grant storage permission to continue." if not self.has_permission_handler 
                        else "Click 'Open Settings' to enable storage permission.",
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
            logger.error(f"Hover error: {e}")
    
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
            logger.info("✓ Permission handler added to page overlay")
        
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
                        on_click=self.set_wallpaper_async,
                        expand=True,
                    ),
                    ft.IconButton(icon=ft.Icons.BUG_REPORT, tooltip="Error Logs", icon_size=24, on_click=self.show_error_dialog, bgcolor=ft.Colors.GREY_800),
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
        logger.info("Starting app")
        
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
        
        logger.info(f"App started | Platform: {'Android' if IS_ANDROID else 'Desktop'} | Images: {len(app.images)}")
        logger.info(f"Permission handler: {'Loaded' if app.has_permission_handler else 'Not available'}")
        logger.info(f"Log file: {LOG_FILE}")
        
    except Exception as e:
        log_error("Fatal error in main", e)
        
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, size=60, color=ft.Colors.RED_400),
                    ft.Text("App Failed to Start", size=20, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e)[:150], size=11, color=ft.Colors.GREY_400, selectable=True, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Text(f"Log: {LOG_FILE}", size=10, color=ft.Colors.GREY_500, selectable=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                padding=40,
                expand=True,
                alignment=ft.alignment.center,
            )
        )

if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("WALLPAPER STUDIO - Starting Application")
        logger.info("=" * 60)
        ft.app(target=main)
    except Exception as e:
        log_error("Fatal startup error", e)
        print("\n" + "=" * 60)
        print("❌ APPLICATION FAILED TO START")
        print("=" * 60)
        if error_log:
            print("\n🐛 RECENT ERRORS:")
            for i, error in enumerate(error_log[-5:], 1):
                print(f"\n[{i}] {error[:200]}")
        else:
            print(f"\n{str(e)}")
            print(traceback.format_exc())
        print(f"\n📄 Full log: {LOG_FILE}")
        print("=" * 60)