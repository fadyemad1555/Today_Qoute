import flet as ft
import os
import traceback
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
import time
import hashlib
from typing import Optional, Tuple, List

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
    """Log errors with timestamp and full traceback"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {error_msg}"
    if exception:
        full_msg = f"{full_msg}\n{str(exception)}\n{traceback.format_exc()}"
    
    error_log.append(full_msg)
    print(f"[ERROR] {full_msg}")
    return full_msg

def get_cache_path(url: str) -> str:
    """Generate consistent cache path for URL"""
    cache_dir = os.path.expanduser("~/.wallpaper_studio_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Use hash for consistent filename
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = os.path.splitext(url.split('?')[0])[-1] or '.jpg'
    return os.path.join(cache_dir, f"{url_hash}{ext}")

def download_image(url: str, dest_path: str, max_retries: int = 3) -> Tuple[bool, str]:
    """Download image with retry logic and better error handling"""
    for attempt in range(max_retries):
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Check if already cached
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                return True, dest_path
            
            # Download with timeout and user agent
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            req.add_header('Accept', 'image/*')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                # Verify content type
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    return False, f"Invalid content type: {content_type}"
                
                # Download with size check
                data = response.read()
                if len(data) == 0:
                    return False, "Downloaded file is empty"
                
                if len(data) > 50 * 1024 * 1024:  # 50MB limit
                    return False, f"Image too large: {len(data) / (1024*1024):.1f}MB"
                
                with open(dest_path, 'wb') as out_file:
                    out_file.write(data)
            
            return True, dest_path
            
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            log_error(f"Download failed for {url}", e)
            return False, error_msg
            
        except urllib.error.URLError as e:
            error_msg = f"Network error: {str(e.reason)}"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            log_error(f"URL error for {url}", e)
            return False, error_msg
            
        except Exception as e:
            log_error(f"Download error on attempt {attempt + 1}", e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return False, f"Unexpected error: {str(e)[:100]}"
    
    return False, "Download failed after all retries"

def set_wallpaper_android(image_path: str) -> Tuple[bool, str]:
    """Set wallpaper using Android WallpaperManager API with enhanced error handling"""
    try:
        if not IS_ANDROID:
            return False, "⚠️ This feature only works on Android devices"
        
        # Validate file exists and is readable
        if not os.path.exists(image_path):
            return False, f"❌ Image file not found: {os.path.basename(image_path)}"
        
        if not os.access(image_path, os.R_OK):
            return False, "❌ Cannot read image file (permission denied)"
        
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 50:
            return False, f"❌ Image too large ({file_size:.1f}MB). Maximum 50MB allowed"
        
        if file_size == 0:
            return False, "❌ Image file is empty"
        
        try:
            from jnius import autoclass, cast
            
            # Get Android context
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            if not PythonActivity or not PythonActivity.mActivity:
                return False, "❌ Failed to access Android activity"
            
            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', currentActivity.getApplicationContext())
            
            if not context:
                return False, "❌ Failed to get application context"
            
            # Load and decode image
            File = autoclass('java.io.File')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            
            file = File(image_path)
            if not file.exists():
                return False, "❌ File validation failed on Android filesystem"
            
            # Decode with options to handle large images
            Options = autoclass('android.graphics.BitmapFactory$Options')
            options = Options()
            options.inJustDecodeBounds = True
            BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
            if options.outWidth <= 0 or options.outHeight <= 0:
                return False, "❌ Invalid image dimensions"
            
            # Decode actual bitmap
            options.inJustDecodeBounds = False
            bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
            if not bitmap:
                return False, "❌ Failed to decode image. Supported: JPG, PNG, WebP"
            
            # Set wallpaper
            WallpaperManager = autoclass('android.app.WallpaperManager')
            manager = WallpaperManager.getInstance(context)
            
            if not manager:
                return False, "❌ WallpaperManager not available"
            
            manager.setBitmap(bitmap)
            bitmap.recycle()  # Free memory
            
            filename = os.path.basename(image_path)
            return True, f"✅ Wallpaper '{filename}' set successfully!"
            
        except ImportError as e:
            log_error("Pyjnius import error", e)
            return False, "❌ Android libraries not available (pyjnius)"
        
        except Exception as e:
            log_error("Android API error", e)
            return False, f"❌ Android error: {str(e)[:100]}"
    
    except Exception as e:
        log_error("Unexpected error in set_wallpaper_android", e)
        return False, f"❌ Critical error: {str(e)[:100]}"

def load_images_from_folder(folder_path: str) -> List[str]:
    """Load images from folder with comprehensive validation"""
    images = []
    
    try:
        if not os.path.exists(folder_path):
            print(f"[INFO] Folder '{folder_path}' not found")
            return images
        
        if not os.path.isdir(folder_path):
            log_error(f"Path '{folder_path}' is not a directory")
            return images
        
        try:
            entries = sorted(os.listdir(folder_path))
        except PermissionError as e:
            log_error(f"Permission denied accessing '{folder_path}'", e)
            return images
        
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
        
        for entry in entries:
            try:
                full_path = os.path.join(folder_path, entry)
                
                if not os.path.isfile(full_path):
                    continue
                
                if entry.lower().endswith(valid_extensions):
                    if os.access(full_path, os.R_OK):
                        size = os.path.getsize(full_path) / (1024 * 1024)
                        if size > 50:
                            print(f"[WARNING] Skipping large file: {entry} ({size:.1f}MB)")
                            continue
                        if size == 0:
                            print(f"[WARNING] Skipping empty file: {entry}")
                            continue
                        images.append(full_path)
                    else:
                        print(f"[WARNING] Cannot read: {entry}")
                        
            except Exception as e:
                log_error(f"Error processing file {entry}", e)
                continue
        
        print(f"[INFO] Loaded {len(images)} images from '{folder_path}'")
        
    except Exception as e:
        log_error(f"Error loading images from {folder_path}", e)
    
    return images

def main(page: ft.Page):
    try:
        # Enhanced page configuration
        page.title = "Wallpaper Studio"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.spacing = 0
        page.scroll = ft.ScrollMode.HIDDEN
        page.bgcolor = "#0a0e1a"
        
        # State management
        class AppState:
            def __init__(self):
                self.images: List[str] = []
                self.selected_image: Optional[str] = None
                self.selected_container: Optional[ft.Container] = None
                self.is_loading: bool = False
                self.download_progress: float = 0
        
        state = AppState()
        
        # UI Components
        status_text = ft.Text(
            "", 
            size=13, 
            weight=ft.FontWeight.W_500, 
            text_align=ft.TextAlign.CENTER
        )
        status_icon = ft.Icon(name=ft.Icons.INFO_OUTLINE, size=18)
        loading_indicator = ft.ProgressRing(
            visible=False, 
            width=20, 
            height=20, 
            stroke_width=3,
            color=ft.Colors.CYAN_400
        )
        
        def show_status(message: str, color: str, icon_name: str = ft.Icons.INFO_OUTLINE):
            """Update status display with animation"""
            status_text.value = message
            status_text.color = color
            status_icon.name = icon_name
            status_icon.color = color
            page.update()
        
        def show_loading(is_loading: bool):
            """Toggle loading state"""
            state.is_loading = is_loading
            loading_indicator.visible = is_loading
            page.update()
        
        def show_snackbar(message: str, bgcolor: str = ft.Colors.BLUE_700):
            """Show enhanced snackbar notification"""
            page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if "success" in message.lower() or "✓" in message or "✅" in message
                            else ft.Icons.ERROR if "error" in message.lower() or "❌" in message
                            else ft.Icons.INFO,
                            color=ft.Colors.WHITE,
                            size=18
                        ),
                        ft.Text(message, color=ft.Colors.WHITE, size=14),
                    ],
                    spacing=10,
                ),
                bgcolor=bgcolor,
                duration=3000,
                behavior=ft.SnackBarBehavior.FLOATING,
                elevation=6,
            )
            page.snack_bar.open = True
            page.update()
        
        def show_error_dialog():
            """Display enhanced error log dialog"""
            if not error_log:
                show_snackbar("✓ No errors recorded", ft.Colors.GREEN_700)
                return
            
            error_content = ft.ListView(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=16),
                                        ft.Text(
                                            f"Error {len(error_log) - i}",
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_400
                                        ),
                                    ],
                                    spacing=6,
                                ),
                                ft.Text(
                                    error,
                                    size=11,
                                    selectable=True,
                                    color=ft.Colors.GREY_300
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=12,
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.RED)),
                    )
                    for i, error in enumerate(reversed(error_log[-10:]))
                ],
                spacing=10,
                padding=10,
                height=400,
            )
            
            dialog = ft.AlertDialog(
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BUG_REPORT_ROUNDED, color=ft.Colors.ORANGE_400, size=24),
                        ft.Text("Error Log", weight=ft.FontWeight.BOLD, size=18),
                        ft.Container(
                            content=ft.Text(
                                f"{len(error_log)}",
                                size=11,
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD
                            ),
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            bgcolor=ft.Colors.RED_700,
                            border_radius=10,
                        ),
                    ],
                    spacing=10,
                ),
                content=error_content,
                actions=[
                    ft.TextButton(
                        "Clear Log",
                        icon=ft.Icons.DELETE_SWEEP,
                        on_click=lambda e: (
                            error_log.clear(),
                            close_dialog(),
                            show_snackbar("✓ Log cleared", ft.Colors.GREEN_700)
                        )
                    ),
                    ft.TextButton(
                        "Close",
                        icon=ft.Icons.CLOSE,
                        on_click=lambda e: close_dialog()
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            def close_dialog():
                dialog.open = False
                page.update()
            
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        
        def on_image_click(e, img_path: str, img_container: ft.Container):
            """Handle image selection with visual feedback"""
            try:
                # Reset previous selection
                if state.selected_container:
                    state.selected_container.border = ft.border.all(
                        2, 
                        ft.Colors.with_opacity(0.3, ft.Colors.WHITE)
                    )
                    state.selected_container.shadow = ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=8,
                        color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                        offset=ft.Offset(0, 2),
                    )
                
                # Set new selection
                state.selected_image = img_path
                state.selected_container = img_container
                
                img_container.border = ft.border.all(3, ft.Colors.CYAN_400)
                img_container.shadow = ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.8, ft.Colors.CYAN_400),
                    offset=ft.Offset(0, 4),
                )
                
                img_name = os.path.basename(img_path) if not img_path.startswith('http') else "Online Image"
                show_snackbar(f"✓ Selected: {img_name[:30]}", ft.Colors.CYAN_700)
                show_status("Ready to set wallpaper", ft.Colors.CYAN_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
                page.update()
                
            except Exception as e:
                log_error("Error in on_image_click", e)
                show_snackbar("❌ Error selecting image", ft.Colors.RED_700)
        
        def clear_selection():
            """Clear current selection"""
            try:
                if state.selected_container:
                    state.selected_container.border = ft.border.all(
                        2,
                        ft.Colors.with_opacity(0.3, ft.Colors.WHITE)
                    )
                    state.selected_container.shadow = ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=8,
                        color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                        offset=ft.Offset(0, 2),
                    )
                
                state.selected_image = None
                state.selected_container = None
                status_text.value = ""
                show_snackbar("Selection cleared", ft.Colors.GREY_700)
                page.update()
            except Exception as e:
                log_error("Error clearing selection", e)
        
        def set_background():
            """Set wallpaper with comprehensive error handling and user feedback"""
            try:
                if state.is_loading:
                    show_snackbar("⏳ Please wait for current operation", ft.Colors.ORANGE_700)
                    return
                
                if not state.selected_image:
                    show_snackbar("⚠️ Please select an image first", ft.Colors.ORANGE_700)
                    return
                
                show_loading(True)
                show_status("Processing...", ft.Colors.CYAN_400, ft.Icons.SYNC)
                
                img_path = state.selected_image
                
                # Download if URL
                if img_path.startswith('http'):
                    show_status("Downloading image...", ft.Colors.CYAN_400, ft.Icons.DOWNLOAD)
                    
                    cache_path = get_cache_path(img_path)
                    
                    success, result = download_image(img_path, cache_path)
                    if not success:
                        show_loading(False)
                        show_status("Download failed", ft.Colors.RED_400, ft.Icons.ERROR_OUTLINE)
                        show_snackbar(f"❌ {result}", ft.Colors.RED_700)
                        return
                    
                    img_path = result
                    show_status("Download complete", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                
                # Set wallpaper
                show_status("Setting wallpaper...", ft.Colors.CYAN_400, ft.Icons.WALLPAPER)
                success, message = set_wallpaper_android(img_path)
                
                show_loading(False)
                
                if success:
                    show_status("Success!", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                    show_snackbar(message, ft.Colors.GREEN_700)
                else:
                    show_status("Failed", ft.Colors.ORANGE_400, ft.Icons.WARNING)
                    show_snackbar(message, ft.Colors.ORANGE_700)
                
                print(f"[INFO] Wallpaper operation: {message}")
                
            except Exception as e:
                show_loading(False)
                log_error("Error in set_background", e)
                show_status("Error", ft.Colors.RED_400, ft.Icons.ERROR_OUTLINE)
                show_snackbar("❌ Unexpected error occurred", ft.Colors.RED_700)
        
        def on_hover(e, container: ft.Container):
            """Enhanced hover effect for images"""
            try:
                if container == state.selected_container:
                    return
                
                if e.data == "true":
                    container.scale = 1.05
                    container.shadow = ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=12,
                        color=ft.Colors.with_opacity(0.5, ft.Colors.CYAN_300),
                        offset=ft.Offset(0, 3),
                    )
                else:
                    container.scale = 1.0
                    container.shadow = ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=8,
                        color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                        offset=ft.Offset(0, 2),
                    )
                page.update()
            except Exception as e:
                log_error("Hover effect error", e)
        
        def create_image_grid():
            """Create enhanced responsive image grid"""
            try:
                grid_items = []
                row_items = []
                
                for i, img in enumerate(state.images):
                    try:
                        # Image container with enhanced styling
                        img_content = ft.Image(
                            src=img,
                            fit=ft.ImageFit.COVER,
                            width=165,
                            height=165,
                            border_radius=12,
                            error_content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Icon(
                                            name=ft.Icons.BROKEN_IMAGE_OUTLINED,
                                            size=40,
                                            color=ft.Colors.GREY_600
                                        ),
                                        ft.Text(
                                            "Load Failed",
                                            size=10,
                                            color=ft.Colors.GREY_500,
                                            weight=ft.FontWeight.W_500
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=8,
                                ),
                                width=165,
                                height=165,
                                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                                border_radius=12,
                                alignment=ft.alignment.center,
                            ),
                        )
                        
                        container = ft.Container(
                            content=img_content,
                            width=165,
                            height=165,
                            border=ft.border.all(2, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
                            border_radius=12,
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
                            animate=150,
                            ink=True,
                            shadow=ft.BoxShadow(
                                spread_radius=0,
                                blur_radius=8,
                                color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                                offset=ft.Offset(0, 2),
                            ),
                        )
                        
                        container.on_click = lambda e, path=img, cont=container: on_image_click(e, path, cont)
                        container.on_hover = lambda e, cont=container: on_hover(e, cont)
                        
                        row_items.append(container)
                        
                        # Create rows of 2 images
                        if (i + 1) % 2 == 0:
                            grid_items.append(ft.Row(
                                controls=row_items,
                                spacing=15,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ))
                            row_items = []
                    except Exception as e:
                        log_error(f"Error creating container for image {i}", e)
                        continue
                
                # Add remaining items
                if row_items:
                    grid_items.append(ft.Row(
                        controls=row_items,
                        spacing=15,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ))
                
                return grid_items
            except Exception as e:
                log_error("Error in create_image_grid", e)
                return [
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.ERROR_OUTLINE, size=50, color=ft.Colors.RED_400),
                                ft.Text("Error loading images", color=ft.Colors.RED_400, size=14),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        padding=40,
                    )
                ]
        
        # Load images
        USE_ONLINE_IMAGES = True
        
        if USE_ONLINE_IMAGES:
            print("[INFO] Using curated online images")
            state.images = [
                "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/2387418/pexels-photo-2387418.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1252869/pexels-photo-1252869.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1287145/pexels-photo-1287145.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1591373/pexels-photo-1591373.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1308940/pexels-photo-1308940.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1761279/pexels-photo-1761279.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/2662116/pexels-photo-2662116.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1526903/pexels-photo-1526903.jpeg?auto=compress&cs=tinysrgb&w=400",
                "https://images.pexels.com/photos/1323550/pexels-photo-1323550.jpeg?auto=compress&cs=tinysrgb&w=400",
            ]
        else:
            state.images = load_images_from_folder("backgrounds")
            if not state.images:
                print("[INFO] No local images found, using default online images")
                state.images = [
                    "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=400",
                    "https://images.pexels.com/photos/2387418/pexels-photo-2387418.jpeg?auto=compress&cs=tinysrgb&w=400",
                    "https://images.pexels.com/photos/1252869/pexels-photo-1252869.jpeg?auto=compress&cs=tinysrgb&w=400",
                    "https://images.pexels.com/photos/1287145/pexels-photo-1287145.jpeg?auto=compress&cs=tinysrgb&w=400",
                ]
        
        # Enhanced Header
        header = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.WALLPAPER_ROUNDED,
                                    size=36,
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
                                        size=26,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE
                                    ),
                                    ft.Text(
                                        "Transform your screen",
                                        size=12,
                                        color=ft.Colors.GREY_400,
                                        weight=ft.FontWeight.W_400
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=14,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                spacing=10,
            ),
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#0f172a", "#1e293b", "#334155"],
            ),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
        )
        
        # Counter Badge
        counter_badge = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.PHOTO_LIBRARY_ROUNDED,
                        size=16,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        f"{len(state.images)} wallpapers available",
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
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.5, ft.Colors.CYAN_700),
                offset=ft.Offset(0, 2),
            ),
        )
        
        # Scrollable image grid
        image_grid_column = ft.Column(
            controls=[
                counter_badge,
                ft.Container(height=16),
                *create_image_grid(),
                ft.Container(height=120),  # Bottom padding for floating button
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        # Enhanced Set Wallpaper Button
        set_btn = ft.Container(
            content=ft.Row(
                controls=[
                    loading_indicator,
                    ft.Icon(
                        ft.Icons.WALLPAPER_ROUNDED,
                        size=22,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "Set Wallpaper",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE
                    ),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=18,
            bgcolor=ft.Colors.CYAN_700,
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=16,
                color=ft.Colors.with_opacity(0.6, ft.Colors.CYAN_700),
                offset=ft.Offset(0, 6),
            ),
            ink=True,
            on_click=lambda e: set_background(),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
        
        # Action buttons row
        action_buttons = ft.Row(
            controls=[
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.CLEAR_ROUNDED,
                        tooltip="Clear Selection",
                        icon_size=24,
                        on_click=lambda e: clear_selection(),
                        icon_color=ft.Colors.GREY_300,
                    ),
                    bgcolor=ft.Colors.GREY_800,
                    border_radius=14,
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=8,
                        color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                        offset=ft.Offset(0, 2),
                    ),
                ),
                ft.Container(content=set_btn, expand=True),
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.BUG_REPORT_ROUNDED,
                        tooltip="View Error Log",
                        icon_size=24,
                        on_click=lambda e: show_error_dialog(),
                        icon_color=ft.Colors.ORANGE_400,
                    ),
                    bgcolor=ft.Colors.GREY_800,
                    border_radius=14,
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=8,
                        color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                        offset=ft.Offset(0, 2),
                    ),
                ),
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        
        # Enhanced bottom bar
        bottom_bar = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[status_icon, status_text],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(vertical=8),
                    ),
                    action_buttons,
                ],
                spacing=10,
            ),
            padding=18,
            bgcolor=ft.Colors.with_opacity(0.95, "#1a1f2e"),
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE))),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                offset=ft.Offset(0, -4),
            ),
        )
        
        # Main layout with proper scrolling
        main_view = ft.Column(
            controls=[
                header,
                ft.Container(
                    content=ft.ListView(
                        controls=[image_grid_column],
                        spacing=0,
                        padding=ft.padding.only(left=15, right=15, top=20, bottom=140),
                        expand=True,
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        
        # Stack layout for floating bottom bar
        page.add(
            ft.Stack(
                controls=[
                    main_view,
                    ft.Container(
                        content=bottom_bar,
                        alignment=ft.alignment.bottom_center,
                    ),
                ],
                expand=True,
            )
        )
        
        # Initial status
        show_status(
            f"Ready • {len(state.images)} images loaded",
            ft.Colors.GREY_400,
            ft.Icons.CHECK_CIRCLE_OUTLINE
        )
        
        print("[INFO] ✓ App initialized successfully")
        print(f"[INFO] Platform: {'Android' if IS_ANDROID else 'Desktop/Emulator'}")
        print(f"[INFO] Images loaded: {len(state.images)}")
        
    except Exception as e:
        log_error("Fatal error in main", e)
        
        # Enhanced error display
        error_display = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.ERROR_OUTLINE_ROUNDED,
                            size=80,
                            color=ft.Colors.RED_400
                        ),
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED_400),
                        border_radius=40,
                        padding=20,
                    ),
                    ft.Text(
                        "Application Failed to Start",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.RED_400,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(
                        content=ft.Text(
                            str(e)[:200],
                            size=12,
                            color=ft.Colors.GREY_400,
                            text_align=ft.TextAlign.CENTER,
                            selectable=True
                        ),
                        padding=20,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                        border_radius=12,
                        width=300,
                    ),
                    ft.ElevatedButton(
                        "View Error Details",
                        icon=ft.Icons.BUG_REPORT_ROUNDED,
                        on_click=lambda e: show_error_dialog(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.RED_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=40,
            expand=True,
            bgcolor="#0a0e1a",
        )
        page.add(error_display)

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as e:
        log_error("Fatal error starting application", e)
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