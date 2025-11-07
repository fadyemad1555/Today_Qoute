import flet as ft
import os
import traceback
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
import time

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
except:
    IS_ANDROID = False

def log_error(error_msg, exception=None):
    """Log errors with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {error_msg}"
    if exception:
        full_msg = f"{full_msg}\n{str(exception)}\n{traceback.format_exc()}"
    
    error_log.append(full_msg)
    print(f"[ERROR] {full_msg}")
    return full_msg

def download_image(url, dest_path, max_retries=3):
    """Download image with retry logic"""
    for attempt in range(max_retries):
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Add timeout and user agent
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(dest_path, 'wb') as out_file:
                    out_file.write(response.read())
            
            return True, dest_path
            
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
                continue
            log_error(f"Failed to download {url} after {max_retries} attempts", e)
            return False, f"Network error: {str(e)}"
        except Exception as e:
            log_error(f"Download error on attempt {attempt + 1}", e)
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return False, str(e)
    
    return False, "Download failed after all retries"

def set_wallpaper_android(image_path):
    """Set wallpaper using Android WallpaperManager API"""
    try:
        if not IS_ANDROID:
            return False, "⚠️ Desktop mode - wallpaper feature only works on Android devices"
        
        if not os.path.exists(image_path):
            return False, f"❌ Image file not found: {image_path}"
        
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 50:
            return False, f"❌ Image too large ({file_size:.1f}MB). Max 50MB."
        
        try:
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            if not PythonActivity or not PythonActivity.mActivity:
                return False, "❌ Failed to access Android context"
            
            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', currentActivity.getApplicationContext())
            
            if not context:
                return False, "❌ Failed to get application context"
            
            File = autoclass('java.io.File')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            
            file = File(image_path)
            if not file.exists():
                return False, f"❌ File does not exist on Android filesystem"
            
            bitmap = BitmapFactory.decodeFile(file.getAbsolutePath())
            if not bitmap:
                return False, "❌ Failed to decode image. Check file format (JPG/PNG)."
            
            WallpaperManager = autoclass('android.app.WallpaperManager')
            manager = WallpaperManager.getInstance(context)
            
            if not manager:
                return False, "❌ WallpaperManager not available"
            
            manager.setBitmap(bitmap)
            
            filename = os.path.basename(image_path)
            return True, f"✅ Wallpaper '{filename}' set successfully!"
            
        except Exception as e:
            log_error("Android Pyjnius error", e)
            return False, f"❌ Android API error: {str(e)[:100]}"
    
    except Exception as e:
        log_error("Unexpected error in set_wallpaper_android", e)
        return False, f"❌ Unexpected error: {str(e)[:100]}"

def load_images_from_folder(folder_path):
    """Load images with comprehensive error handling"""
    images = []
    
    try:
        if not os.path.exists(folder_path):
            print(f"[INFO] Folder '{folder_path}' not found. Using default images.")
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
                        # Verify file size is reasonable
                        size = os.path.getsize(full_path) / (1024 * 1024)
                        if size > 50:
                            print(f"[WARNING] Skipping large file: {entry} ({size:.1f}MB)")
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
        # Page configuration
        page.title = "Wallpaper Studio"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.window.width = 400
        page.window.height = 900
        
        # State management
        class AppState:
            def __init__(self):
                self.images = []
                self.selected_image = None
                self.selected_container = None
                self.is_loading = False
                self.show_errors = False
        
        state = AppState()
        
        # UI Components
        status_text = ft.Text("", size=14, weight="w500", text_align=ft.TextAlign.CENTER)
        status_icon = ft.Icon(name=ft.Icons.INFO_OUTLINE, size=20)
        loading_indicator = ft.ProgressBar(visible=False, color=ft.Colors.BLUE_400)
        
        def show_status(message, color, icon_name=ft.Icons.INFO_OUTLINE):
            """Update status display"""
            status_text.value = message
            status_text.color = color
            status_icon.name = icon_name
            status_icon.color = color
            page.update()
        
        def show_loading(is_loading):
            """Toggle loading state"""
            state.is_loading = is_loading
            loading_indicator.visible = is_loading
            page.update()
        
        def show_error_dialog():
            """Display error log in a dialog"""
            if not error_log:
                show_status("No errors recorded", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
                return
            
            error_content = ft.ListView(
                controls=[
                    ft.Text(error, size=12, selectable=True)
                    for error in error_log[-10:]  # Show last 10 errors
                ],
                spacing=10,
                padding=20,
                height=400,
            )
            
            dialog = ft.AlertDialog(
                title=ft.Text("Error Log", weight="bold"),
                content=error_content,
                actions=[
                    ft.TextButton("Clear Log", on_click=lambda e: (error_log.clear(), close_dialog())),
                    ft.TextButton("Close", on_click=lambda e: close_dialog()),
                ],
            )
            
            def close_dialog():
                dialog.open = False
                page.update()
            
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        
        def on_image_click(e, img_path, img_container):
            """Handle image selection with error handling"""
            try:
                # Reset previous selection
                if state.selected_container:
                    state.selected_container.border = ft.border.all(2, ft.Colors.with_opacity(0.2, ft.Colors.WHITE))
                    state.selected_container.shadow = None
                
                # Set new selection
                state.selected_image = img_path
                state.selected_container = img_container
                
                img_container.border = ft.border.all(4, ft.Colors.BLUE_400)
                img_container.shadow = ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.6, ft.Colors.BLUE_400),
                    offset=ft.Offset(0, 4),
                )
                
                img_name = os.path.basename(img_path) if not img_path.startswith('http') else img_path.split('/')[-1].split('?')[0]
                show_status(f"Selected: {img_name}", ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE_OUTLINE)
                
            except Exception as e:
                log_error("Error in on_image_click", e)
                show_status("Error selecting image", ft.Colors.RED_400, ft.Icons.ERROR_OUTLINE)
        
        def clear_selection():
            """Clear current selection"""
            try:
                if state.selected_container:
                    state.selected_container.border = ft.border.all(2, ft.Colors.with_opacity(0.2, ft.Colors.WHITE))
                    state.selected_container.shadow = None
                
                state.selected_image = None
                state.selected_container = None
                status_text.value = ""
                page.update()
            except Exception as e:
                log_error("Error clearing selection", e)
        
        def set_background():
            """Set wallpaper with comprehensive error handling"""
            try:
                if state.is_loading:
                    show_status("Please wait, operation in progress...", ft.Colors.ORANGE_400, ft.Icons.HOURGLASS_EMPTY)
                    return
                
                if not state.selected_image:
                    show_status("Please select an image first", ft.Colors.ORANGE_400, ft.Icons.WARNING_AMBER)
                    return
                
                show_loading(True)
                show_status("Processing...", ft.Colors.BLUE_400, ft.Icons.SYNC)
                
                img_path = state.selected_image
                
                # Download if URL
                if img_path.startswith('http'):
                    show_status("Downloading image...", ft.Colors.BLUE_400, ft.Icons.DOWNLOAD)
                    
                    cache_dir = os.path.expanduser("~/.background_manager_cache")
                    filename = img_path.split('/')[-1].split('?')[0] or "image.jpg"
                    cache_path = os.path.join(cache_dir, filename)
                    
                    success, result = download_image(img_path, cache_path)
                    if not success:
                        show_loading(False)
                        show_status(f"Download failed: {result[:50]}", ft.Colors.RED_400, ft.Icons.ERROR_OUTLINE)
                        return
                    
                    img_path = result
                
                # Set wallpaper
                show_status("Setting wallpaper...", ft.Colors.BLUE_400, ft.Icons.WALLPAPER)
                success, message = set_wallpaper_android(img_path)
                
                show_loading(False)
                
                if success:
                    show_status(message, ft.Colors.GREEN_400, ft.Icons.CHECK_CIRCLE)
                else:
                    show_status(message, ft.Colors.ORANGE_400, ft.Icons.WARNING)
                
                print(f"[INFO] Wallpaper operation: {message}")
                
            except Exception as e:
                show_loading(False)
                error_msg = log_error("Error in set_background", e)
                show_status("Error setting wallpaper", ft.Colors.RED_400, ft.Icons.ERROR_OUTLINE)
        
        def on_hover(e, container):
            """Hover effect for images"""
            try:
                if e.data == "true" and container != state.selected_container:
                    container.scale = 1.05
                    container.shadow = ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=10,
                        color=ft.Colors.with_opacity(0.3, ft.Colors.BLUE),
                        offset=ft.Offset(0, 3),
                    )
                else:
                    if container != state.selected_container:
                        container.scale = 1.0
                        container.shadow = None
                page.update()
            except Exception as e:
                log_error("Hover effect error", e)
        
        def create_image_grid():
            """Create responsive image grid"""
            try:
                grid_items = []
                row_items = []
                
                for i, img in enumerate(state.images):
                    try:
                        # Image container with loading state
                        container = ft.Container(
                            content=ft.Image(
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
                                            ft.Text("Failed to load", size=11, color=ft.Colors.GREY_500),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    width=165,
                                    height=165,
                                    bgcolor=ft.Colors.GREY_900,
                                    border_radius=12,
                                    alignment=ft.alignment.center,
                                ),
                            ),
                            width=165,
                            height=165,
                            border=ft.border.all(2, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                            border_radius=12,
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            animate_scale=ft.animation.Animation(150, ft.AnimationCurve.EASE_OUT),
                            animate_opacity=200,
                        )
                        
                        container.on_click = lambda e, path=img, cont=container: on_image_click(e, path, cont)
                        container.on_hover = lambda e, cont=container: on_hover(e, cont)
                        
                        row_items.append(container)
                        
                        if (i + 1) % 2 == 0:
                            grid_items.append(ft.Row(
                                controls=row_items,
                                spacing=10,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ))
                            row_items = []
                    except Exception as e:
                        log_error(f"Error creating container for image {i}", e)
                        continue
                
                if row_items:
                    grid_items.append(ft.Row(
                        controls=row_items,
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ))
                
                return grid_items
            except Exception as e:
                log_error("Error in create_image_grid", e)
                return [ft.Text("Error loading images", color=ft.Colors.RED_400)]
        
        # Always use online images for now (comment this line to load from folder)
        USE_ONLINE_IMAGES = True
        
        if USE_ONLINE_IMAGES:
            print("[INFO] Using online images")
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
            # Load images from local folder
            state.images = load_images_from_folder("backgrounds")
            
            # Fallback to default images if none found
            if not state.images:
                print("[INFO] No local images found, using default online images")
                state.images = [
                    "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=400",
                    "https://images.pexels.com/photos/2387418/pexels-photo-2387418.jpeg?auto=compress&cs=tinysrgb&w=400",
                    "https://images.pexels.com/photos/1252869/pexels-photo-1252869.jpeg?auto=compress&cs=tinysrgb&w=400",
                    "https://images.pexels.com/photos/1287145/pexels-photo-1287145.jpeg?auto=compress&cs=tinysrgb&w=400",
                ]
        
        # Build UI
        header = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WALLPAPER, size=36, color=ft.Colors.BLUE_400),
                            ft.Column(
                                controls=[
                                    ft.Text("Wallpaper Studio", size=28, weight="bold", color=ft.Colors.WHITE),
                                    ft.Text("Transform your device", size=13, color=ft.Colors.GREY_400, italic=True),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=15,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.padding.only(left=25, right=25, top=20, bottom=20),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#1a1a2e", "#16213e"],
            ),
            border_radius=ft.border_radius.only(bottom_left=25, bottom_right=25),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 5),
            ),
        )
        
        counter_badge = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PHOTO_LIBRARY, size=16, color=ft.Colors.WHITE),
                    ft.Text(f"{len(state.images)} Available", size=12, color=ft.Colors.WHITE, weight="bold"),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor=ft.Colors.BLUE_700,
            border_radius=20,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLUE),
                offset=ft.Offset(0, 2),
            ),
        )
        
        image_scroll = ft.Container(
            content=ft.Column(
                controls=[
                    counter_badge,
                    ft.Container(height=15),
                    *create_image_grid(),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            expand=True,
        )
        
        set_btn = ft.ElevatedButton(
            text="Set as Wallpaper",
            on_click=lambda e: set_background(),
            icon=ft.Icons.WALLPAPER_OUTLINED,
            expand=True,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                color=ft.Colors.WHITE,
                bgcolor={
                    ft.ControlState.DEFAULT: ft.Colors.BLUE_700,
                    ft.ControlState.HOVERED: ft.Colors.BLUE_600,
                },
            ),
        )
        
        clear_btn = ft.IconButton(
            icon=ft.Icons.CLEAR_OUTLINED,
            tooltip="Clear selection",
            icon_size=24,
            on_click=lambda e: clear_selection(),
            icon_color=ft.Colors.GREY_400,
        )
        
        error_btn = ft.IconButton(
            icon=ft.Icons.BUG_REPORT_OUTLINED,
            tooltip="View error log",
            icon_size=24,
            on_click=lambda e: show_error_dialog(),
            icon_color=ft.Colors.ORANGE_400,
        )
        
        button_container = ft.Container(
            content=ft.Column(
                controls=[
                    loading_indicator,
                    ft.Row(
                        controls=[set_btn, clear_btn, error_btn],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
            ),
            padding=20,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            border_radius=ft.border_radius.only(top_left=20, top_right=20),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, -3),
            ),
        )
        
        status_container = ft.Container(
            content=ft.Row(
                controls=[status_icon, status_text],
                spacing=12,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=16,
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
            visible=True,
        )
        
        main_content = ft.Column(
            controls=[
                header,
                image_scroll,
                status_container,
                button_container,
            ],
            spacing=0,
            expand=True,
        )
        
        page.add(main_content)
        print("[INFO] App initialized successfully")
        print(f"[INFO] Platform: {'Android' if IS_ANDROID else 'Desktop'}")
        
    except Exception as e:
        log_error("Fatal error in main", e)
        error_display = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=60, color=ft.Colors.RED_400),
                    ft.Text("App Failed to Initialize", size=20, weight="bold", color=ft.Colors.RED_400),
                    ft.Text(str(e)[:200], size=12, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=40,
            expand=True,
        )
        page.add(error_display)

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as e:
        log_error("Fatal error in ft.app", e)
        print("=" * 50)
        print("APP FAILED TO START")
        print("=" * 50)
        for error in error_log:
            print(error)
        print("=" * 50)t
