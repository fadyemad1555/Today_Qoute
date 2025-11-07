import flet as ft
import os
import traceback
import urllib.request
import urllib.error
from pathlib import Path




# Global error log
error_log = []

# Better platform detection - check if actually running on Android
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
            return False, "⚠ Desktop mode - wallpaper feature only works on Android devices"
        
        # Validate image path exists
        if not os.path.exists(image_path):
            return False, f"✗ Image file not found: {image_path}"
        
        # Check file size
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
            
        except Exception as e:
            log_error("Android Pyjnius error", e)
            return False, "✗ Android API unavailable"
    
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
        page.window.height = 900
        
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
                "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=400",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400",
            ]
        
        selected_image = ft.Ref()
        status_text = ft.Text("", size=14, color=ft.Colors.GREEN, weight="w500")
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
                        selected_container_ref.current.shadow = None
                    except Exception as e:
                        log_error("Error resetting previous border", e)
                
                # Set new selection
                selected_image.current = img_path
                selected_container_ref.current = img_container
                img_container.border = ft.Border(
                    left=ft.BorderSide(4, ft.Colors.BLUE_400),
                    right=ft.BorderSide(4, ft.Colors.BLUE_400),
                    top=ft.BorderSide(4, ft.Colors.BLUE_400),
                    bottom=ft.BorderSide(4, ft.Colors.BLUE_400),
                )
                img_container.shadow = ft.BoxShadow(
                    spread_radius=4,
                    blur_radius=12,
                    color=ft.Colors.with_opacity(0.5, ft.Colors.BLUE_400),
                    offset=ft.Offset(0, 4),
                )
                
                img_name = os.path.basename(img_path) if os.path.exists(img_path) else img_path.split('/')[-1]
                status_text.value = f"✓ Selected: {img_name}"
                status_text.color = ft.Colors.GREEN_400
                page.update()
            except Exception as e:
                log_error("Error in on_image_click", e)
                status_text.value = "✗ Error selecting image"
                status_text.color = ft.Colors.RED_400
                page.update()
        
        def set_background():
            try:
                if is_loading.current:
                    status_text.value = "⏳ Please wait, operation in progress..."
                    page.update()
                    return
                
                if not selected_image.current:
                    status_text.value = "⚠ Please select an image first"
                    status_text.color = ft.Colors.ORANGE_400
                    page.update()
                    return
                
                # Show loading
                is_loading.current = True
                status_text.value = "⏳ Setting wallpaper..."
                status_text.color = ft.Colors.BLUE_400
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
                        status_text.color = ft.Colors.ORANGE_400
                        page.update()
                        return
                    
                    img_path = result
                
                success, message = set_wallpaper_android(img_path)
                
                is_loading.current = False
                
                if success:
                    status_text.value = message
                    status_text.color = ft.Colors.GREEN_400
                else:
                    status_text.value = message
                    status_text.color = ft.Colors.ORANGE_400
                
                print(f"[INFO] Wallpaper operation: {message}")
                page.update()
            except Exception as e:
                is_loading.current = False
                log_error("Error in set_background", e)
                status_text.value = "✗ Error setting wallpaper. Check logs."
                status_text.color = ft.Colors.RED_400
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
                                width=160,
                                height=160,
                                error_content=ft.Container(
                                    content=ft.Column(
                                        controls=[
                                            ft.Icon(
                                                name=ft.Icons.IMAGE_NOT_SUPPORTED,
                                                size=40,
                                                color=ft.Colors.GREY_600
                                            ),
                                            ft.Text("Failed to load", size=10, color=ft.Colors.GREY_600),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    width=160,
                                    height=160,
                                    bgcolor=ft.Colors.GREY_900,
                                    alignment=ft.alignment.center,
                                ),
                            ),
                            width=160,
                            height=160,
                            border=ft.Border(
                                left=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                                right=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                                top=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                                bottom=ft.BorderSide(2, ft.Colors.TRANSPARENT),
                            ),
                            border_radius=15,
                            ink=True,
                            on_hover=lambda e, cont=None: _on_hover(e, cont),
                        )
                        
                        row_items.append(container)
                        container.on_click = lambda e, path=img, cont=container: on_image_click(e, path, cont)
                        container.on_hover = lambda e, cont=container: _on_hover(e, cont)
                        
                        if (i + 1) % 2 == 0:
                            grid_items.append(ft.Row(
                                controls=row_items,
                                spacing=12,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ))
                            row_items = []
                    except Exception as e:
                        log_error(f"Error creating container for image {i}", e)
                        continue
                
                if row_items:
                    grid_items.append(ft.Row(
                        controls=row_items,
                        spacing=12,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ))
                
                return grid_items
            except Exception as e:
                log_error("Error in create_image_grid", e)
                return []
        
        def _on_hover(e, container):
            """Hover effect for images"""
            try:
                if e.data == "true" and container != selected_container_ref.current:
                    container.shadow = ft.BoxShadow(
                        spread_radius=2,
                        blur_radius=8,
                        color=ft.Colors.with_opacity(0.4, ft.Colors.BLUE),
                        offset=ft.Offset(0, 3),
                    )
                else:
                    if container != selected_container_ref.current:
                        container.shadow = None
                page.update()
            except Exception as e:
                log_error("Hover effect error", e)
        
        try:
            # Premium gradient header
            header = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("🎨 Wallpaper Studio", size=32, weight="bold", color=ft.Colors.WHITE),
                        ft.Text("Customize your device with beautiful wallpapers", size=13, color=ft.Colors.GREY_300, italic=True),
                    ],
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=25,
                bgcolor="#1a1a2e",
                border_radius=ft.border_radius.only(bottom_left=25, bottom_right=25),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=15,
                    color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    offset=ft.Offset(0, 5),
                ),
            )
            
            # Image counter badge with gradient feel
            counter_badge = ft.Container(
                content=ft.Text(f"📸  {len(images)} Wallpapers", size=12, color=ft.Colors.WHITE, weight="bold"),
                padding=ft.padding.symmetric(horizontal=14, vertical=7),
                bgcolor=ft.Colors.BLUE_700,
                border_radius=25,
                alignment=ft.alignment.center,
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=8,
                    color=ft.Colors.with_opacity(0.3, ft.Colors.BLUE),
                    offset=ft.Offset(0, 2),
                ),
            )
            
            # Image grid container with better styling
            image_column = ft.Column(
                controls=create_image_grid(),
                spacing=12,
            )
            
            image_scroll = ft.Container(
                content=image_column,
                padding=20,
                expand=True,
            )
            
            # Premium Set Wallpaper button
            set_btn = ft.ElevatedButton(
                text="Set Wallpaper",
                on_click=lambda e: set_background(),
                icon=ft.Icons.WALLPAPER_OUTLINED,
                expand=True,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=14),
                    padding=ft.padding.symmetric(vertical=14),
                    color=ft.Colors.WHITE,
                ),
            )
            
            clear_btn = ft.IconButton(
                ft.Icons.CLEAR_OUTLINED,
                tooltip="Clear selection",
                icon_size=22,
                on_click=lambda e: (
                    selected_container_ref.current.update() if selected_container_ref.current else None,
                    setattr(selected_image, 'current', None),
                    setattr(status_text, 'value', ''),
                    page.update()
                ),
            )
            
            button_row = ft.Container(
                content=ft.Row(
                    controls=[set_btn, clear_btn],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=20,
                bgcolor=ft.Colors.SURFACE,
                border_radius=ft.border_radius.only(top_left=20, top_right=20),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=10,
                    color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                    offset=ft.Offset(0, -2),
                ),
            )
            
            # Stylish status bar
            status_container = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(name=ft.Icons.INFO_OUTLINE, size=18, color=ft.Colors.GREEN_400)
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=16,
                bgcolor=ft.Colors.SURFACE,
                border_radius=12,
                border=ft.border.all(1, ft.Colors.GREY_800),
            )
            
            # Footer with counter
            footer = ft.Container(
                content=ft.Row(
                    controls=[counter_badge],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=15,
                bgcolor=ft.Colors.GREY_900,
            )
            
            # Main scrollable content
            main_scroll = ft.Column(
                controls=[
                    header,
                    image_scroll,
                    button_row,
                    status_container,
                    footer,
                ],
                expand=True,
            )
            
            page.add(main_scroll)
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