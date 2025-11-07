import flet as ft
import os
import traceback
import urllib.request
import urllib.error
from pathlib import Path

# Global error log
error_log = []

# Check if on Android platform
IS_ANDROID = False
try:
    from jnius import autoclass
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

def log_error(error_msg, exception=None):
    """Log errors to global list and print"""
    full_msg = error_msg
    if exception:
        full_msg = f"{error_msg}\n{str(exception)}\n{traceback.format_exc()}"
    
    error_log.append(full_msg)
    print(f"[ERROR] {full_msg}")

def download_image(url, dest_path):
    """Download image from URL to local path"""
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        urllib.request.urlretrieve(url, dest_path)
        return True, dest_path
    except urllib.error.URLError as e:
        log_error(f"Failed to download {url}", e)
        return False, str(e)
    except Exception as e:
        log_error(f"Download error", e)
        return False, str(e)

def set_wallpaper_android(image_path):
    """
    Set wallpaper using Android WallpaperManager API via Pyjnius
    """
    try:
        if not IS_ANDROID:
            return False, "⚠ Android API not available (desktop testing mode)"
        
        # Validate image path exists
        if not os.path.exists(image_path):
            return False, f"✗ Image file not found: {image_path}"
        
        # Check file size (warn if too large)
        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 50:
            return False, f"✗ Image too large ({file_size:.1f}MB). Max 50MB."
        
        try:
            from jnius import autoclass, cast
            
            # Get the Android activity context
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            if not PythonActivity or not PythonActivity.mActivity:
                return False, "✗ Failed to access Android context"
            
            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', currentActivity.getApplicationContext())
            
            if not context:
                return False, "✗ Failed to get application context"
            
            # Load the image file
            File = autoclass('java.io.File')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            
            file = File(image_path)
            if not file.exists():
                return False, f"✗ File does not exist on Android filesystem"
            
            bitmap = BitmapFactory.decodeFile(file.getAbsolutePath())
            if not bitmap:
                return False, "✗ Failed to decode image. Check file format (JPG/PNG)."
            
            # Set the wallpaper
            WallpaperManager = autoclass('android.app.WallpaperManager')
            manager = WallpaperManager.getInstance(context)
            
            if not manager:
                return False, "✗ WallpaperManager not available"
            
            manager.setBitmap(bitmap)
            
            filename = os.path.basename(image_path)
            return True, f"✓ Wallpaper '{filename}' set successfully!"
            
        except AttributeError as e:
            log_error("Android attribute error", e)
            return False, f"✗ Android API error: Missing method/class"
        except Exception as e:
            log_error("Wallpaper setting failed", e)
            return False, f"✗ Failed to set wallpaper: {str(e)[:100]}"
    
    except Exception as e:
        log_error("Unexpected error in set_wallpaper_android", e)
        return False, f"✗ Unexpected error: {str(e)[:100]}"

def load_images_from_folder(folder_path):
    """Load images from folder with error handling"""
    images = []
    
    try:
        if not os.path.exists(folder_path):
            print(f"[INFO] Folder '{folder_path}' not found. Using default images.")
            return images
        
        if not os.path.isdir(folder_path):
            print(f"[ERROR] Path '{folder_path}' is not a directory")
            return images
        
        try:
            entries = os.listdir(folder_path)
        except PermissionError:
            log_error(f"Permission denied accessing '{folder_path}'")
            return images
        
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        
        for entry in entries:
            try:
                full_path = os.path.join(folder_path, entry)
                
                if not os.path.isfile(full_path):
                    continue
                
                if entry.lower().endswith(valid_extensions):
                    if os.access(full_path, os.R_OK):
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
        page.title = "Background Manager"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.window.width = 400
        page.window.height = 800
        
        # Load images
        images = load_images_from_folder("backgrounds")
        
        # Fallback to default images if none found
        if not images:
            print("[INFO] No local images found, using default Unsplash images")
            images = [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400",
                "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=400",
                "https://images.unsplash.com/photo-1494783367193-149034c05e41?w=400",
                "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe3e?w=400",
                "https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=400",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400",
            ]
        
        selected_image = ft.Ref()
        status_text = ft.Text("", size=14, color=ft.Colors.GREEN)
        selected_container_ref = ft.Ref()
        is_loading = ft.Ref()
        is_loading.current = False
        
        def on_image_click(e, img_path, img_container):
            try:
                # Reset previous selection border
                if selected_container_ref.current:
                    try:
                        selected_container_ref.current.border = ft.Border(
                            left=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                            right=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                            top=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                            bottom=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                        )
                    except Exception as e:
                        log_error("Error resetting previous border", e)
                
                # Set new selection
                selected_image.current = img_path
                selected_container_ref.current = img_container
                img_container.border = ft.Border(
                    left=ft.BorderSide(4, ft.Colors.BLUE),
                    right=ft.BorderSide(4, ft.Colors.BLUE),
                    top=ft.BorderSide(4, ft.Colors.BLUE),
                    bottom=ft.BorderSide(4, ft.Colors.BLUE),
                )
                
                img_name = os.path.basename(img_path) if os.path.exists(img_path) else img_path.split('/')[-1]
                status_text.value = f"✓ Selected: {img_name}"
                status_text.color = ft.Colors.GREEN
                page.update()
            except Exception as e:
                log_error("Error in on_image_click", e)
                status_text.value = "✗ Error selecting image"
                status_text.color = ft.Colors.RED
                page.update()
        
        def set_background():
            try:
                if is_loading.current:
                    status_text.value = "⏳ Please wait, operation in progress..."
                    page.update()
                    return
                
                if not selected_image.current:
                    status_text.value = "⚠ Please select an image first"
                    status_text.color = ft.Colors.ORANGE
                    page.update()
                    return
                
                # Show loading
                is_loading.current = True
                status_text.value = "⏳ Setting wallpaper..."
                status_text.color = ft.Colors.BLUE
                page.update()
                
                img_path = selected_image.current
                
                # If URL, download first
                if img_path.startswith('http'):
                    status_text.value = "⏳ Downloading image..."
                    page.update()
                    
                    cache_dir = os.path.expanduser("~/.background_manager_cache")
                    filename = img_path.split('/')[-1].split('?')[0] or "image.jpg"
                    cache_path = os.path.join(cache_dir, filename)
                    
                    success, result = download_image(img_path, cache_path)
                    if not success:
                        is_loading.current = False
                        status_text.value = f"✗ Failed to download: {result}"
                        status_text.color = ft.Colors.ORANGE
                        page.update()
                        return
                    
                    img_path = result
                
                success, message = set_wallpaper_android(img_path)
                
                is_loading.current = False
                
                if success:
                    status_text.value = message
                    status_text.color = ft.Colors.GREEN
                else:
                    status_text.value = message
                    status_text.color = ft.Colors.ORANGE
                
                print(f"[INFO] Wallpaper operation: {message}")
                page.update()
            except Exception as e:
                is_loading.current = False
                log_error("Error in set_background", e)
                status_text.value = "✗ Error setting wallpaper. Check logs."
                status_text.color = ft.Colors.RED
                page.update()
        
        def create_image_grid():
            try:
                grid_items = []
                row_items = []
                
                for i, img in enumerate(images):
                    try:
                        container = ft.Container(
                            content=ft.Image(
                                src=img,
                                fit=ft.ImageFit.COVER,
                                width=150,
                                height=150,
                                error_content=ft.Container(
                                    content=ft.Icon(
                                        name=ft.Icons.IMAGE_NOT_SUPPORTED,
                                        size=40,
                                        color=ft.Colors.GREY
                                    ),
                                    width=150,
                                    height=150,
                                    alignment=ft.alignment.center,
                                ),
                            ),
                            width=150,
                            height=150,
                            border=ft.Border(
                                left=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                                right=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                                top=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                                bottom=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                            ),
                        )
                        
                        row_items.append(container)
                        container.on_click = lambda e, path=img, cont=container: on_image_click(e, path, cont)
                        
                        if (i + 1) % 2 == 0:
                            grid_items.append(ft.Row(controls=row_items, spacing=10))
                            row_items = []
                    except Exception as e:
                        log_error(f"Error creating container for image {i}", e)
                        continue
                
                if row_items:
                    grid_items.append(ft.Row(controls=row_items, spacing=10))
                
                return grid_items
            except Exception as e:
                log_error("Error in create_image_grid", e)
                return []
        
        try:
            # Header
            header = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Background Manager", size=28, weight="bold"),
                        ft.Text(f"Total: {len(images)} images", size=12, color=ft.Colors.GREY_400),
                    ],
                    spacing=5,
                ),
                padding=20,
                bgcolor=ft.Colors.PRIMARY,
            )
            
            # Image grid with scroll
            image_column = ft.Column(
                controls=create_image_grid(),
                spacing=10,
            )
            
            image_scroll = ft.Container(
                content=image_column,
                padding=15,
                expand=True,
            )
            
            # Button row wrapped in container for padding
            button_row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Set Background",
                            on_click=lambda e: set_background(),
                            icon=ft.Icons.WALLPAPER,
                            expand=True,
                        ),
                        ft.IconButton(
                            ft.Icons.CLEAR,
                            tooltip="Clear selection",
                            on_click=lambda e: (
                                selected_container_ref.current.update() if selected_container_ref.current else None,
                                setattr(selected_image, 'current', None),
                                setattr(status_text, 'value', ''),
                                page.update()
                            ),
                        ),
                    ],
                    spacing=10,
                ),
                padding=15,
            )
            
            # Status bar
            status_bar = ft.Container(
                content=status_text,
                padding=15,
                bgcolor=ft.Colors.SURFACE,
            )
            
            # Main content
            content = ft.Column(
                controls=[
                    header,
                    ft.Divider(height=1),
                    image_scroll,
                    ft.Divider(height=1),
                    button_row,
                    status_bar,
                ],
                expand=True,
            )
            
            page.add(content)
            print("[INFO] App initialized successfully")
        except Exception as e:
            log_error("Error building UI", e)
            error_dialog = ft.Text(f"UI Error: {str(e)[:100]}", color=ft.Colors.RED)
            page.add(error_dialog)
    
    except Exception as e:
        log_error("Fatal error in main", e)
        raise

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as e:
        log_error("Fatal error in ft.app", e)
        print("App failed to start. Check errors above.")