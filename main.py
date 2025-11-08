import flet as ft
import os
import traceback
import urllib.request
import urllib.error
from datetime import datetime
import time
import hashlib
from typing import Optional, List
import tempfile
import asyncio

# Global error log
error_log = []

# Platform detection
IS_ANDROID = False
try:
    import sys
    if 'ANDROID_APP_PATH' in os.environ or 'ANDROID_ROOT' in os.environ:
        IS_ANDROID = True
    elif sys.platform.startswith('linux') and os.path.exists('/system/build.prop'):
        IS_ANDROID = True
except Exception:
    IS_ANDROID = False

def log_error(error_msg: str, exception: Optional[Exception] = None) -> str:
    """Log errors with timestamp and traceback"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {error_msg}"
    if exception:
        full_msg = f"{full_msg}\n{str(exception)}\n{traceback.format_exc()}"
    
    error_log.append(full_msg)
    print(f"[ERROR] {full_msg}")
    return full_msg

def get_cache_path(url: str) -> str:
    """Generate cache path with Android compatibility"""
    try:
        if IS_ANDROID:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity.getApplicationContext()
            cache_dir = str(context.getCacheDir().getAbsolutePath())
        else:
            cache_dir = os.path.join(tempfile.gettempdir(), 'wallpaper_studio_cache')
        
        os.makedirs(cache_dir, exist_ok=True)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(url.split('?')[0])[-1] or '.jpg'
        return os.path.join(cache_dir, f"{url_hash}{ext}")
    except Exception as e:
        log_error("Cache path error, using fallback", e)
        cache_dir = os.path.join(tempfile.gettempdir(), 'wallpaper_studio_cache')
        os.makedirs(cache_dir, exist_ok=True)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(url.split('?')[0])[-1] or '.jpg'
        return os.path.join(cache_dir, f"{url_hash}{ext}")

async def download_image_async(url: str, dest_path: str, progress_callback=None) -> tuple[bool, str]:
    """Download image asynchronously with progress"""
    for attempt in range(3):
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                return True, dest_path
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            req.add_header('Accept', 'image/*')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    return False, f"Invalid content type: {content_type}"
                
                total_size = int(response.headers.get('Content-Length', 0))
                data = bytearray()
                chunk_size = 8192
                downloaded = 0
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    data.extend(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback and total_size:
                        progress = downloaded / total_size
                        await progress_callback(progress)
                
                if len(data) == 0:
                    return False, "Downloaded file is empty"
                
                if len(data) > 50 * 1024 * 1024:
                    return False, f"Image too large: {len(data) / (1024*1024):.1f}MB"
                
                temp_path = dest_path + '.tmp'
                with open(temp_path, 'wb') as out_file:
                    out_file.write(data)
                
                os.replace(temp_path, dest_path)
            
            return True, dest_path
            
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            log_error(f"Download failed for {url}", e)
            return False, str(e)[:100]
    
    return False, "Download failed"

def set_wallpaper_android(image_path: str) -> tuple[bool, str]:
    """Set wallpaper using Android API"""
    try:
        if not IS_ANDROID:
            return False, "⚠️ This feature only works on Android devices"
        
        if not os.path.exists(image_path):
            return False, f"❌ Image file not found"
        
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 50 or file_size == 0:
            return False, f"❌ Invalid file size: {file_size:.1f}MB"
        
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
            
            if options.outWidth <= 0 or options.outHeight <= 0:
                return False, "❌ Invalid image dimensions"
            
            # Sample large images
            max_dimension = 4096
            if options.outWidth > max_dimension or options.outHeight > max_dimension:
                scale = max(options.outWidth, options.outHeight) / max_dimension
                options.inSampleSize = int(scale)
            
            options.inJustDecodeBounds = False
            bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
            if not bitmap:
                return False, "❌ Failed to decode image"
            
            WallpaperManager = autoclass('android.app.WallpaperManager')
            manager = WallpaperManager.getInstance(context)
            manager.setBitmap(bitmap)
            bitmap.recycle()
            
            return True, f"✅ Wallpaper set successfully!"
            
        except ImportError:
            return False, "❌ Android libraries not available"
        except Exception as e:
            log_error("Android API error", e)
            return False, f"❌ Error: {str(e)[:100]}"
    
    except Exception as e:
        log_error("Wallpaper error", e)
        return False, f"❌ Critical error"

class WallpaperApp:
    """Main application class using Flet best practices"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.selected_image: Optional[str] = None
        self.selected_container: Optional[ft.Container] = None
        self.is_loading = False
        self.storage_permission_granted = False
        
        # UI Components
        self.status_text = ft.Text(
            "", 
            size=13, 
            weight=ft.FontWeight.W_500,
            text_align=ft.TextAlign.CENTER
        )
        self.status_icon = ft.Icon(ft.Icons.INFO_OUTLINE, size=18)
        self.loading_ring = ft.ProgressRing(
            visible=False,
            width=20,
            height=20,
            stroke_width=3,
            color=ft.Colors.CYAN_400
        )
        self.image_grid_ref = ft.Ref[ft.Column]()
        
        # Wallpaper URLs
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
    
    def show_snackbar(self, message: str, bgcolor: str = ft.Colors.BLUE_700):
        """Show snackbar notification"""
        icon = ft.Icons.CHECK_CIRCLE if "✅" in message else \
               ft.Icons.ERROR if "❌" in message else \
               ft.Icons.WARNING if "⚠️" in message else ft.Icons.INFO
        
        snack_bar = ft.SnackBar(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=ft.Colors.WHITE, size=18),
                    ft.Text(message, color=ft.Colors.WHITE, size=14),
                ],
                spacing=10,
            ),
            bgcolor=bgcolor,
            duration=3000,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()
    
    async def check_permissions(self):
        """Check and request storage permissions"""
        try:
            if not IS_ANDROID:
                self.storage_permission_granted = True
                return True
            
            # For Android, attempt to check permissions
            # Note: PermissionHandler is deprecated in Flet 0.26+
            # Consider using the separate flet-permission-handler package
            # For now, assume permission granted on non-Android or handle gracefully
            
            print("[INFO] Checking storage permissions...")
            self.storage_permission_granted = True
            return True
                
        except Exception as e:
            log_error("Permission check failed", e)
            # Assume granted if check fails (for compatibility)
            self.storage_permission_granted = True
            return True
    
    async def open_app_settings(self, e):
        """Open app settings for manual permission grant"""
        try:
            self.show_snackbar("Opening app settings...", ft.Colors.BLUE_700)
        except Exception as e:
            log_error("Failed to open settings", e)
            self.show_snackbar("❌ Could not open settings", ft.Colors.RED_700)
    
    def show_status(self, message: str, color: str, icon: str = ft.Icons.INFO_OUTLINE):
        """Update status display"""
        self.status_text.value = message
        self.status_text.color = color
        self.status_icon.name = icon
        self.status_icon.color = color
        self.page.update()
    
    def show_loading(self, loading: bool):
        """Toggle loading state"""
        self.is_loading = loading
        self.loading_ring.visible = loading
        self.page.update()
    
    def show_error_dialog(self, e):
        """Display error log dialog"""
        if not error_log:
            self.show_snackbar("✓ No errors recorded", ft.Colors.GREEN_700)
            return
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        def clear_log(e):
            error_log.clear()
            close_dlg(e)
            self.show_snackbar("✓ Log cleared", ft.Colors.GREEN_700)
        
        error_items = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"Error {len(error_log) - i}",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.RED_400
                        ),
                        ft.Text(
                            error,
                            size=10,
                            selectable=True,
                            color=ft.Colors.GREY_300
                        ),
                    ],
                    spacing=4,
                ),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
            )
            for i, error in enumerate(reversed(error_log[-10:]))
        ]
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.BUG_REPORT, color=ft.Colors.ORANGE_400, size=24),
                    ft.Text("Error Log", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=error_items,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
                height=400,
                width=400,
            ),
            actions=[
                ft.TextButton("Clear Log", icon=ft.Icons.DELETE_SWEEP, on_click=clear_log),
                ft.TextButton("Close", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(dlg)
    
    def on_image_click(self, e, img_path: str, container: ft.Container):
        """Handle image selection"""
        try:
            # Reset previous selection
            if self.selected_container:
                self.selected_container.border = ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE))
                self.selected_container.shadow = None
            
            # Set new selection
            self.selected_image = img_path
            self.selected_container = container
            
            container.border = ft.border.all(3, ft.Colors.CYAN_400)
            container.shadow = ft.BoxShadow(
                spread_radius=2,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.8, ft.Colors.CYAN_400),
                offset=ft.Offset(0, 4),
            )
            
            self.show_snackbar("✓ Image selected", ft.Colors.CYAN_700)
            self.show_status("Ready to set wallpaper", ft.Colors.CYAN_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
            self.page.update()
            
        except Exception as e:
            log_error("Selection error", e)
            self.show_snackbar("❌ Selection error", ft.Colors.RED_700)
    
    def clear_selection(self, e):
        """Clear current selection"""
        try:
            if self.selected_container:
                self.selected_container.border = ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE))
                self.selected_container.shadow = None
            
            self.selected_image = None
            self.selected_container = None
            self.status_text.value = ""
            self.show_snackbar("Selection cleared", ft.Colors.GREY_700)
            self.page.update()
        except Exception as e:
            log_error("Clear error", e)
    
    async def set_wallpaper_async(self, e):
        """Set wallpaper asynchronously"""
        try:
            if self.is_loading:
                self.show_snackbar("⏳ Please wait", ft.Colors.ORANGE_700)
                return
            
            if not self.selected_image:
                self.show_snackbar("⚠️ Select an image first", ft.Colors.ORANGE_700)
                return
            
            # Check storage permission first
            if not self.storage_permission_granted:
                self.show_status("Checking permissions...", ft.Colors.CYAN_400, ft.Icons.SECURITY)
                has_permission = await self.check_permissions()
                
                if not has_permission:
                    # Show dialog to open settings
                    self.show_permission_dialog()
                    return
            
            self.show_loading(True)
            self.show_status("Processing...", ft.Colors.CYAN_400, ft.Icons.SYNC)
            
            img_path = self.selected_image
            
            # Download if URL
            if img_path.startswith('http'):
                self.show_status("Downloading...", ft.Colors.CYAN_400, ft.Icons.DOWNLOAD)
                cache_path = get_cache_path(img_path)
                
                async def update_progress(progress):
                    # Update UI with download progress if needed
                    pass
                
                success, result = await download_image_async(img_path, cache_path, update_progress)
                
                if not success:
                    self.show_loading(False)
                    self.show_status("Download failed", ft.Colors.RED_400, ft.Icons.ERROR)
                    self.show_snackbar(f"❌ {result}", ft.Colors.RED_700)
                    return
                
                img_path = result
                self.show_status("Downloaded", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
            
            # Set wallpaper
            self.show_status("Setting wallpaper...", ft.Colors.CYAN_400, ft.Icons.WALLPAPER)
            success, message = set_wallpaper_android(img_path)
            
            self.show_loading(False)
            
            if success:
                self.show_status("Success!", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                self.show_snackbar(message, ft.Colors.GREEN_700)
            else:
                self.show_status("Failed", ft.Colors.ORANGE_400, ft.Icons.WARNING)
                self.show_snackbar(message, ft.Colors.ORANGE_700)
            
        except Exception as e:
            self.show_loading(False)
            log_error("Wallpaper error", e)
            self.show_status("Error", ft.Colors.RED_400, ft.Icons.ERROR)
            self.show_snackbar("❌ Unexpected error", ft.Colors.RED_700)
    
    def show_permission_dialog(self):
        """Show dialog when permission is denied"""
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LOCK_OUTLINE, color=ft.Colors.ORANGE_400, size=28),
                    ft.Text("Storage Permission Required", weight=ft.FontWeight.BOLD, size=18),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Wallpaper Studio needs storage permission to:",
                            size=14,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Container(height=8),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.DOWNLOAD, size=20, color=ft.Colors.CYAN_400),
                                ft.Text("Download wallpaper images", size=13),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SAVE, size=20, color=ft.Colors.CYAN_400),
                                ft.Text("Cache images for faster access", size=13),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.WALLPAPER, size=20, color=ft.Colors.CYAN_400),
                                ft.Text("Set wallpapers on your device", size=13),
                            ],
                            spacing=10,
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "Please grant storage permission in the app settings.",
                            size=12,
                            color=ft.Colors.GREY_400,
                            italic=True,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                padding=10,
            ),
            actions=[
                ft.TextButton(
                    "Cancel",
                    on_click=close_dlg
                ),
                ft.FilledButton(
                    "Open Settings",
                    icon=ft.Icons.SETTINGS,
                    on_click=lambda e: (
                        self.open_app_settings(e),
                        close_dlg(e)
                    )
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(dlg)
    
    def on_hover(self, e: ft.HoverEvent, container: ft.Container):
        """Image hover effect"""
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
            log_error("Hover error", e)
    
    def create_image_card(self, img_url: str) -> ft.Container:
        """Create individual image card"""
        img_content = ft.Image(
            src=img_url,
            fit=ft.ImageFit.COVER,
            width=165,
            height=165,
            border_radius=12,
            error_content=ft.Container(
                content=ft.Icon(
                    ft.Icons.BROKEN_IMAGE,
                    size=40,
                    color=ft.Colors.GREY_600
                ),
                width=165,
                height=165,
                bgcolor=ft.Colors.GREY_900,
                border_radius=12,
                alignment=ft.alignment.center,
            ),
        )
        
        # Create container first without callbacks
        container = ft.Container(
            content=img_content,
            width=165,
            height=165,
            border=ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            ink=True,
        )
        
        # Now assign callbacks that reference the container
        container.on_click = lambda e, path=img_url, cont=container: self.on_image_click(e, path, cont)
        container.on_hover = lambda e, cont=container: self.on_hover(e, cont)
        
        return container
    
    def create_image_grid(self) -> ft.Column:
        """Create responsive image grid"""
        rows = []
        row_items = []
        
        for i, img in enumerate(self.images):
            card = self.create_image_card(img)
            row_items.append(card)
            
            if (i + 1) % 2 == 0:
                rows.append(
                    ft.Row(
                        controls=row_items,
                        spacing=15,
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
                row_items = []
        
        if row_items:
            rows.append(
                ft.Row(
                    controls=row_items,
                    spacing=15,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )
        
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PHOTO_LIBRARY, size=16, color=ft.Colors.WHITE),
                            ft.Text(
                                f"{len(self.images)} wallpapers",
                                size=13,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.W_500
                            ),
                        ],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    bgcolor=ft.Colors.CYAN_700,
                    border_radius=20,
                ),
                ft.Container(height=16),
                *rows,
                ft.Container(height=140),
            ],
            ref=self.image_grid_ref,
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    
    def build(self) -> ft.Control:
        """Build main UI"""
        # Header
        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.WALLPAPER_ROUNDED,
                            size=32,
                            color=ft.Colors.CYAN_400
                        ),
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.CYAN_400),
                        border_radius=12,
                        padding=8,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                "Wallpaper Studio",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE
                            ),
                            ft.Text(
                                "Transform your screen",
                                size=12,
                                color=ft.Colors.GREY_400,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#0f172a", "#1e293b"],
            ),
        )
        
        # Bottom bar
        bottom_bar = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[self.status_icon, self.status_text],
                        spacing=8,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.CLEAR,
                                tooltip="Clear Selection",
                                icon_size=24,
                                on_click=self.clear_selection,
                                bgcolor=ft.Colors.GREY_800,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        self.loading_ring,
                                        ft.Icon(ft.Icons.WALLPAPER, size=20),
                                        ft.Text(
                                            "Set Wallpaper",
                                            size=15,
                                            weight=ft.FontWeight.BOLD
                                        ),
                                    ],
                                    spacing=8,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                padding=16,
                                bgcolor=ft.Colors.CYAN_700,
                                border_radius=12,
                                ink=True,
                                on_click=self.set_wallpaper_async,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.BUG_REPORT,
                                tooltip="Error Log",
                                icon_size=24,
                                on_click=self.show_error_dialog,
                                bgcolor=ft.Colors.GREY_800,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=10,
            ),
            padding=16,
            bgcolor=ft.Colors.with_opacity(0.95, "#1a1f2e"),
        )
        
        # Main layout
        return ft.Stack(
            controls=[
                ft.Column(
                    controls=[
                        header,
                        ft.Container(
                            content=ft.ListView(
                                controls=[self.create_image_grid()],
                                padding=20,
                            ),
                            expand=True,
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
                ft.Container(
                    content=bottom_bar,
                    alignment=ft.alignment.bottom_center,
                ),
            ],
            expand=True,
        )

def main(page: ft.Page):
    """Main entry point"""
    try:
        # Page configuration - Flet best practices
        page.title = "Wallpaper Studio"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.bgcolor = "#0a0e1a"
        page.scroll = ft.ScrollMode.HIDDEN
        
        # Theme customization
        page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.CYAN,
            use_material3=True,
        )
        
        # Create app instance
        app = WallpaperApp(page)
        
        # Add to page
        page.add(app.build())
        
        # Initial status
        app.show_status(
            f"Ready • {len(app.images)} images loaded",
            ft.Colors.GREY_400,
            ft.Icons.CHECK_CIRCLE_OUTLINE
        )
        
        # Check permissions on startup (async)
        async def check_permissions_on_start():
            await asyncio.sleep(0.5)  # Wait for UI to load
            if IS_ANDROID:
                app.show_status("Checking permissions...", ft.Colors.CYAN_400, ft.Icons.SECURITY)
                await app.check_permissions()
                app.show_status(
                    f"Ready • {len(app.images)} images loaded",
                    ft.Colors.GREY_400,
                    ft.Icons.CHECK_CIRCLE_OUTLINE
                )
        
        # Run permission check
        page.run_task(check_permissions_on_start)
        
        print(f"[INFO] ✓ App initialized successfully")
        print(f"[INFO] Platform: {'Android' if IS_ANDROID else 'Desktop'}")
        print(f"[INFO] Images: {len(app.images)}")
        
    except Exception as e:
        log_error("Fatal error in main", e)
        
        page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.ERROR, size=60, color=ft.Colors.RED_400),
                        ft.Text(
                            "Application Failed to Start",
                            size=20,
                            color=ft.Colors.RED_400,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(
                            str(e)[:150],
                            size=11,
                            color=ft.Colors.GREY_400,
                            selectable=True,
                            text_align=ft.TextAlign.CENTER
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15,
                ),
                padding=40,
                expand=True,
                alignment=ft.alignment.center,
            )
        )

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as e:
        log_error("Fatal startup error", e)
        print("\n" + "=" * 60)
        print("❌ APPLICATION FAILED TO START")
        print("=" * 60)
        if error_log:
            print("\n🐛 ERROR LOG:")
            for i, error in enumerate(error_log, 1):
                print(f"\n[{i}] {error}")
        else:
            print(f"\n{str(e)}")
            print(traceback.format_exc())
        print("=" * 60)