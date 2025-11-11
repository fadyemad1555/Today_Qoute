# import flet as ft
# import os
# import sys
# import tempfile
# from datetime import datetime

# # Platform detection
# IS_ANDROID = False
# try:
#     if 'ANDROID_APP_PATH' in os.environ or 'ANDROID_ROOT' in os.environ:
#         IS_ANDROID = True
#     elif sys.platform.startswith('linux') and os.path.exists('/system/build.prop'):
#         IS_ANDROID = True
# except Exception as e:
#     print(f"Platform detection error: {e}")

# print(f"Platform: {'Android' if IS_ANDROID else 'Desktop'}")

# class PermissionTestApp:
#     def __init__(self, page: ft.Page):
#         self.page = page
#         self.logs = []
        
#         # UI Components - Initialize FIRST
#         self.log_container = ft.Column(
#             spacing=5,
#             scroll=ft.ScrollMode.AUTO,
#             height=400,
#         )
        
#         self.status_text = ft.Text(
#             "Ready to test permissions",
#             size=16,
#             weight=ft.FontWeight.BOLD,
#         )
        
#         # Try to import permission handler AFTER UI components
#         self.permission_handler = None
#         self.has_permission_handler = False
        
#         try:
#             import flet_permission_handler as fph
#             self.fph = fph
#             self.permission_handler = fph.PermissionHandler()
#             self.has_permission_handler = True
#             self.add_log("✓ flet-permission-handler loaded", "green")
#         except ImportError:
#             self.add_log("✗ flet-permission-handler not installed", "red")
        
#         # Permission status
#         self.storage_granted = False
        
#     def add_log(self, message: str, color: str = "white"):
#         """Add log entry"""
#         timestamp = datetime.now().strftime("%H:%M:%S")
#         log_entry = ft.Container(
#             content=ft.Row([
#                 ft.Text(f"[{timestamp}]", size=11, color="grey"),
#                 ft.Text(message, size=12, color=color),
#             ], spacing=8),
#             padding=5,
#             bgcolor="#1a1a1a",
#             border_radius=5,
#         )
#         self.logs.append(log_entry)
#         self.log_container.controls.append(log_entry)
#         self.page.update()
#         print(f"[{timestamp}] {message}")
    
#     async def check_storage_permission(self, e):
#         """Check storage permission"""
#         try:
#             self.add_log("=" * 50, "cyan")
#             self.add_log("CHECKING STORAGE PERMISSION", "yellow")
            
#             if not IS_ANDROID:
#                 self.add_log("Not Android - permissions not required", "green")
#                 self.storage_granted = True
#                 self.status_text.value = "✅ Not Android - No permissions needed"
#                 self.status_text.color = "green"
#                 self.page.update()
#                 return
            
#             if not self.has_permission_handler:
#                 self.add_log("❌ Permission handler not available", "red")
#                 self.status_text.value = "❌ Install flet-permission-handler"
#                 self.status_text.color = "red"
#                 self.page.update()
#                 return
            
#             self.add_log("Checking STORAGE permission...", "cyan")
#             status = await self.permission_handler.check_permission(
#                 self.fph.PermissionType.STORAGE
#             )
            
#             self.add_log(f"Status: {status}", "yellow")
            
#             if status == self.fph.PermissionStatus.GRANTED:
#                 self.add_log("✅ STORAGE permission GRANTED", "green")
#                 self.storage_granted = True
#                 self.status_text.value = "✅ Storage Permission Granted"
#                 self.status_text.color = "green"
#             elif status == self.fph.PermissionStatus.DENIED:
#                 self.add_log("⚠️ STORAGE permission DENIED", "orange")
#                 self.storage_granted = False
#                 self.status_text.value = "⚠️ Storage Permission Denied"
#                 self.status_text.color = "orange"
#             elif status == self.fph.PermissionStatus.PERMANENTLY_DENIED:
#                 self.add_log("🚫 STORAGE permission PERMANENTLY DENIED", "red")
#                 self.storage_granted = False
#                 self.status_text.value = "🚫 Permission Permanently Denied"
#                 self.status_text.color = "red"
#             else:
#                 self.add_log(f"❓ Unknown status: {status}", "orange")
#                 self.storage_granted = False
#                 self.status_text.value = "❓ Unknown Permission Status"
#                 self.status_text.color = "orange"
            
#             self.page.update()
            
#         except Exception as e:
#             self.add_log(f"❌ Error: {str(e)}", "red")
#             self.status_text.value = "❌ Error checking permission"
#             self.status_text.color = "red"
#             self.page.update()
    
#     async def request_storage_permission(self, e):
#         """Request storage permission"""
#         try:
#             self.add_log("=" * 50, "cyan")
#             self.add_log("REQUESTING STORAGE PERMISSION", "yellow")
            
#             if not IS_ANDROID:
#                 self.add_log("Not Android - no request needed", "green")
#                 return
            
#             if not self.has_permission_handler:
#                 self.add_log("❌ Permission handler not available", "red")
#                 return
            
#             self.add_log("Requesting STORAGE permission...", "cyan")
#             result = await self.permission_handler.request_permission(
#                 self.fph.PermissionType.STORAGE
#             )
            
#             self.add_log(f"Result: {result}", "yellow")
            
#             if result == self.fph.PermissionStatus.GRANTED:
#                 self.add_log("✅ Permission GRANTED by user", "green")
#                 self.storage_granted = True
#                 self.status_text.value = "✅ Permission Granted!"
#                 self.status_text.color = "green"
#             else:
#                 self.add_log("❌ Permission DENIED by user", "red")
#                 self.storage_granted = False
#                 self.status_text.value = "❌ Permission Denied"
#                 self.status_text.color = "red"
            
#             self.page.update()
            
#         except Exception as e:
#             self.add_log(f"❌ Error: {str(e)}", "red")
#             self.status_text.value = "❌ Error requesting permission"
#             self.status_text.color = "red"
#             self.page.update()
    
#     async def test_file_write(self, e):
#         """Test file write capability"""
#         try:
#             self.add_log("=" * 50, "cyan")
#             self.add_log("TESTING FILE WRITE", "yellow")
            
#             test_dir = tempfile.gettempdir()
#             test_file = os.path.join(test_dir, "wallpaper_test.txt")
            
#             self.add_log(f"Test directory: {test_dir}", "cyan")
#             self.add_log(f"Test file: {test_file}", "cyan")
            
#             # Write test
#             self.add_log("Writing test file...", "cyan")
#             with open(test_file, 'w') as f:
#                 f.write(f"Test write at {datetime.now()}")
#             self.add_log("✅ Write successful", "green")
            
#             # Read test
#             self.add_log("Reading test file...", "cyan")
#             with open(test_file, 'r') as f:
#                 content = f.read()
#             self.add_log(f"✅ Read successful: {content[:30]}", "green")
            
#             # Delete test
#             self.add_log("Deleting test file...", "cyan")
#             os.remove(test_file)
#             self.add_log("✅ Delete successful", "green")
            
#             self.status_text.value = "✅ File Operations Successful"
#             self.status_text.color = "green"
#             self.page.update()
            
#         except Exception as e:
#             self.add_log(f"❌ File operation failed: {str(e)}", "red")
#             self.status_text.value = "❌ File Operations Failed"
#             self.status_text.color = "red"
#             self.page.update()
    
#     async def test_set_wallpaper(self, e):
#         """Test set wallpaper (Android only)"""
#         try:
#             self.add_log("=" * 50, "cyan")
#             self.add_log("TESTING SET WALLPAPER", "yellow")
            
#             if not IS_ANDROID:
#                 self.add_log("❌ Not Android - wallpaper setting only works on Android", "red")
#                 self.status_text.value = "❌ Android Only Feature"
#                 self.status_text.color = "red"
#                 self.page.update()
#                 return
            
#             if not self.storage_granted:
#                 self.add_log("⚠️ Storage permission not granted", "orange")
#                 self.status_text.value = "⚠️ Grant permission first"
#                 self.status_text.color = "orange"
#                 self.page.update()
#                 return
            
#             # Use a cached/downloaded image from temp directory
#             test_dir = tempfile.gettempdir()
            
#             # Look for any existing image files
#             self.add_log(f"Looking for test images in: {test_dir}", "cyan")
            
#             test_image = None
#             for file in os.listdir(test_dir):
#                 if file.endswith(('.jpg', '.jpeg', '.png')):
#                     test_image = os.path.join(test_dir, file)
#                     self.add_log(f"✅ Found test image: {file}", "green")
#                     break
            
#             # If no image found, try to download one
#             if not test_image:
#                 self.add_log("No image found, downloading sample...", "cyan")
#                 import urllib.request
                
#                 sample_url = "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=400"
#                 test_image = os.path.join(test_dir, "wallpaper_test.jpg")
                
#                 try:
#                     req = urllib.request.Request(sample_url)
#                     req.add_header('User-Agent', 'Mozilla/5.0')
                    
#                     with urllib.request.urlopen(req, timeout=10) as response:
#                         data = response.read()
#                         with open(test_image, 'wb') as f:
#                             f.write(data)
                    
#                     self.add_log(f"✅ Downloaded test image: {len(data)} bytes", "green")
#                 except Exception as dl_error:
#                     self.add_log(f"❌ Download failed: {str(dl_error)}", "red")
#                     self.status_text.value = "❌ No test image available"
#                     self.status_text.color = "red"
#                     self.page.update()
#                     return
            
#             # Check file exists and has size
#             if not os.path.exists(test_image):
#                 self.add_log("❌ Test image file not found", "red")
#                 self.status_text.value = "❌ Image Not Found"
#                 self.status_text.color = "red"
#                 self.page.update()
#                 return
            
#             file_size = os.path.getsize(test_image) / 1024
#             self.add_log(f"Image size: {file_size:.1f} KB", "cyan")
            
#             # Try to set wallpaper
#             self.add_log("Setting wallpaper...", "cyan")
            
#             from jnius import autoclass, cast
            
#             PythonActivity = autoclass('org.kivy.android.PythonActivity')
#             currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
#             context = cast('android.content.Context', currentActivity.getApplicationContext())
            
#             File = autoclass('java.io.File')
#             BitmapFactory = autoclass('android.graphics.BitmapFactory')
#             Options = autoclass('android.graphics.BitmapFactory$Options')
#             WallpaperManager = autoclass('android.app.WallpaperManager')
            
#             file = File(test_image)
            
#             # Decode with options
#             options = Options()
#             options.inJustDecodeBounds = True
#             BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
#             self.add_log(f"Image dimensions: {options.outWidth}x{options.outHeight}", "cyan")
            
#             # Check if valid
#             if options.outWidth <= 0 or options.outHeight <= 0:
#                 self.add_log("❌ Invalid image dimensions", "red")
#                 self.status_text.value = "❌ Invalid Image"
#                 self.status_text.color = "red"
#                 self.page.update()
#                 return
            
#             # Decode actual bitmap
#             options.inJustDecodeBounds = False
#             bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), options)
            
#             if not bitmap:
#                 self.add_log("❌ Failed to decode image", "red")
#                 self.status_text.value = "❌ Image Decode Failed"
#                 self.status_text.color = "red"
#                 self.page.update()
#                 return
            
#             self.add_log("✅ Image decoded successfully", "green")
            
#             # Set wallpaper
#             manager = WallpaperManager.getInstance(context)
#             manager.setBitmap(bitmap)
#             bitmap.recycle()
            
#             self.add_log("✅ WALLPAPER SET SUCCESSFULLY!", "green")
#             self.status_text.value = "✅ Wallpaper Set Successfully!"
#             self.status_text.color = "green"
            
#             self.page.update()
            
#         except Exception as e:
#             self.add_log(f"❌ Wallpaper error: {str(e)}", "red")
#             self.add_log(f"Error type: {type(e).__name__}", "red")
#             import traceback
#             tb = traceback.format_exc()
#             # Split traceback into lines and log each
#             for line in tb.split('\n')[:5]:  # First 5 lines only
#                 if line.strip():
#                     self.add_log(line[:100], "red")
#             self.status_text.value = "❌ Wallpaper Setting Failed"
#             self.status_text.color = "red"
#             self.page.update()
    
#     async def open_settings(self, e):
#         """Open app settings"""
#         try:
#             self.add_log("=" * 50, "cyan")
#             self.add_log("OPENING APP SETTINGS", "yellow")
            
#             if not IS_ANDROID:
#                 self.add_log("❌ Not Android", "red")
#                 return
            
#             if self.has_permission_handler:
#                 success = await self.permission_handler.open_app_settings()
#                 if success:
#                     self.add_log("✅ Settings opened", "green")
#                 else:
#                     self.add_log("❌ Failed to open settings", "red")
#             else:
#                 self.add_log("❌ Permission handler not available", "red")
            
#         except Exception as e:
#             self.add_log(f"❌ Error: {str(e)}", "red")
    
#     def clear_logs(self, e):
#         """Clear all logs"""
#         self.logs.clear()
#         self.log_container.controls.clear()
#         self.add_log("Logs cleared", "cyan")
#         self.status_text.value = "Ready to test permissions"
#         self.status_text.color = "white"
#         self.page.update()
    
#     def build(self):
#         """Build UI"""
        
#         # Add permission handler to overlay if available
#         if self.permission_handler:
#             self.page.overlay.append(self.permission_handler)
#             print("✓ Permission handler added to overlay")
        
#         return ft.Container(
#             content=ft.Column([
#                 # Header
#                 ft.Container(
#                     content=ft.Column([
#                         ft.Row([
#                             ft.Icon(ft.Icons.SECURITY, size=40, color=ft.Colors.CYAN_400),
#                             ft.Column([
#                                 ft.Text("Permission Test", size=28, weight=ft.FontWeight.BOLD),
#                                 ft.Text(f"Platform: {'Android' if IS_ANDROID else 'Desktop'}", size=12, color=ft.Colors.GREY_400),
#                             ], spacing=2),
#                         ], spacing=15),
#                         ft.Container(height=10),
#                         self.status_text,
#                     ], spacing=5),
#                     padding=20,
#                     bgcolor=ft.Colors.BLUE_GREY_900,
#                     border_radius=10,
#                 ),
                
#                 ft.Container(height=10),
                
#                 # Control Buttons
#                 ft.Container(
#                     content=ft.Column([
#                         ft.Text("Step 1: Check Permission", size=14, weight=ft.FontWeight.BOLD),
#                         ft.ElevatedButton(
#                             "Check Storage Permission",
#                             icon=ft.Icons.SEARCH,
#                             on_click=self.check_storage_permission,
#                             width=300,
#                         ),
                        
#                         ft.Divider(height=20),
                        
#                         ft.Text("Step 2: Request Permission", size=14, weight=ft.FontWeight.BOLD),
#                         ft.ElevatedButton(
#                             "Request Storage Permission",
#                             icon=ft.Icons.HOME,
#                             on_click=self.request_storage_permission,
#                             width=300,
#                             bgcolor=ft.Colors.ORANGE_700,
#                         ),
                        
#                         ft.Divider(height=20),
                        
#                         ft.Text("Step 3: Test File Operations", size=14, weight=ft.FontWeight.BOLD),
#                         ft.ElevatedButton(
#                             "Test File Read/Write",
#                             icon=ft.Icons.FILE_COPY,
#                             on_click=self.test_file_write,
#                             width=300,
#                             bgcolor=ft.Colors.GREEN_700,
#                         ),
                        
#                         ft.Divider(height=20),
                        
#                         ft.Text("Step 4: Test Set Wallpaper", size=14, weight=ft.FontWeight.BOLD),
#                         ft.ElevatedButton(
#                             "Test Set Wallpaper (Android)",
#                             icon=ft.Icons.WALLPAPER,
#                             on_click=self.test_set_wallpaper,
#                             width=300,
#                             bgcolor=ft.Colors.PURPLE_700,
#                         ),
                        
#                         ft.Divider(height=20),
                        
#                         ft.Row([
#                             ft.ElevatedButton(
#                                 "Open Settings",
#                                 icon=ft.Icons.SETTINGS,
#                                 on_click=self.open_settings,
#                             ),
#                             ft.ElevatedButton(
#                                 "Clear Logs",
#                                 icon=ft.Icons.CLEAR,
#                                 on_click=self.clear_logs,
#                             ),
#                         ], spacing=10),
#                     ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
#                     padding=20,
#                     bgcolor=ft.Colors.BLUE_GREY_900,
#                     border_radius=10,
#                 ),
                
#                 ft.Container(height=10),
                
#                 # Log Container
#                 ft.Container(
#                     content=ft.Column([
#                         ft.Row([
#                             ft.Icon(ft.Icons.TERMINAL, size=20),
#                             ft.Text("Activity Log", size=16, weight=ft.FontWeight.BOLD),
#                         ], spacing=10),
#                         ft.Divider(height=1),
#                         self.log_container,
#                     ], spacing=10),
#                     padding=15,
#                     bgcolor=ft.Colors.BLUE_GREY_900,
#                     border_radius=10,
#                     expand=True,
#                 ),
                
#             ], spacing=10, expand=True, scroll=ft.ScrollMode.AUTO),
#             padding=20,
#             expand=True,
#         )

# def main(page: ft.Page):
#     page.title = "Permission Test App"
#     page.theme_mode = ft.ThemeMode.DARK
#     page.padding = 0
#     page.bgcolor = "#0a0e1a"
    
#     app = PermissionTestApp(page)
#     page.add(app.build())
    
#     # Add initial log
#     app.add_log("App started successfully", "green")
#     app.add_log(f"Platform: {'Android' if IS_ANDROID else 'Desktop'}", "cyan")
#     app.add_log(f"Permission handler: {'Available' if app.has_permission_handler else 'Not installed'}", 
#                 "green" if app.has_permission_handler else "orange")

# if __name__ == "__main__":
#     ft.app(target=main)




import requests

r=requests.get("https://zenquotes.io/api/random").json()
print(r[0]["q"])