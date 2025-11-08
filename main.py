import flet as ft
import os
import sys
import tempfile
from datetime import datetime

# Platform detection
IS_ANDROID = False
try:
    if 'ANDROID_APP_PATH' in os.environ or 'ANDROID_ROOT' in os.environ:
        IS_ANDROID = True
    elif sys.platform.startswith('linux') and os.path.exists('/system/build.prop'):
        IS_ANDROID = True
except Exception as e:
    print(f"Platform detection error: {e}")

print(f"Platform: {'Android' if IS_ANDROID else 'Desktop'}")

class PermissionTestApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.logs = []
        
        # UI Components - Initialize FIRST
        self.log_container = ft.Column(
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            height=400,
        )
        
        self.status_text = ft.Text(
            "جاهز لتجربة الطرق - Ready",
            size=16,
            weight=ft.FontWeight.BOLD,
        )
        
        # Try to import permission handler AFTER UI components
        self.permission_handler = None
        self.has_permission_handler = False
        
        try:
            import flet_permission_handler as fph
            self.fph = fph
            self.permission_handler = fph.PermissionHandler()
            self.has_permission_handler = True
            self.add_log("✓ flet-permission-handler loaded", "green")
        except ImportError:
            self.add_log("✗ flet-permission-handler not installed", "red")
        
        # Permission status
        self.storage_granted = False
        
    def add_log(self, message: str, color: str = "white"):
        """Add log entry"""
        m=""
        n=0
        for x in message.split(" "):
            m+=x
            n+=1
            if n==2:
                n=0
                m+="\n"
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = ft.Container(
            content=ft.Row([
                ft.Text(f"[{timestamp}]", size=11, color="grey"),
                ft.Text(m, size=12, color=color),
            ], spacing=8),
            padding=5,
            bgcolor="#1a1a1a",
            border_radius=5,
        )
        self.logs.append(log_entry)
        self.log_container.controls.append(log_entry)
        self.page.update()
        print(f"[{timestamp}] {message}")
    
    async def run_single_method(self, e, method_num):
        """تشغيل طريقة واحدة محددة"""
        try:
            self.add_log("=" * 50, "cyan")
            self.add_log(f"🚀 تشغيل الطريقة {method_num}", "yellow")
            
            if not IS_ANDROID:
                self.add_log("❌ التطبيق يعمل فقط على أندرويد", "red")
                self.status_text.value = "❌ أندرويد فقط"
                self.status_text.color = "red"
                self.page.update()
                return
            
            # الحصول على الصورة
            image_path = self.get_test_image()
            if not image_path:
                self.add_log("❌ فشل تحميل الصورة", "red")
                self.status_text.value = "❌ لا توجد صورة"
                self.status_text.color = "red"
                self.page.update()
                return
            
            # التحقق من الملف
            if not os.path.exists(image_path):
                self.add_log("❌ الصورة غير موجودة", "red")
                self.status_text.value = "❌ الصورة غير موجودة"
                self.status_text.color = "red"
                self.page.update()
                return
            
            file_size = os.path.getsize(image_path) / 1024
            self.add_log(f"📁 حجم الصورة: {file_size:.1f} كيلوبايت", "cyan")
            
            # تشغيل الطريقة المحددة
            methods = {
                1: ("الطريقة 1: Direct Bitmap", self.method1_direct_bitmap),
                2: ("الطريقة 2: Input Stream", self.method2_input_stream),
                3: ("الطريقة 3: Content URI", self.method3_content_uri),
                4: ("الطريقة 4: With Scaling", self.method4_with_scaling),
                5: ("الطريقة 5: Intent", self.method5_intent),
            }
            
            method_name, method_func = methods[method_num]
            self.add_log(f"▶️ جاري تشغيل {method_name}...", "cyan")
            
            success = await method_func(image_path)
            
            if success:
                self.add_log(f"🎉 نجحت {method_name}!", "green")
                self.status_text.value = f"✅ نجح: {method_name}"
                self.status_text.color = "green"
            else:
                self.add_log(f"❌ فشلت {method_name}", "red")
                self.status_text.value = f"❌ فشل: {method_name}"
                self.status_text.color = "red"
            
            self.page.update()
            
        except Exception as e:
            self.add_log(f"❌ خطأ: {str(e)}", "red")
            self.status_text.value = "❌ حدث خطأ"
            self.status_text.color = "red"
            self.page.update()
    
        """Check storage permission"""
        try:
            self.add_log("=" * 50, "cyan")
            self.add_log("CHECKING STORAGE PERMISSION", "yellow")
            
            if not IS_ANDROID:
                self.add_log("Not Android - permissions not required", "green")
                self.storage_granted = True
                self.status_text.value = "✅ Not Android - No permissions needed"
                self.status_text.color = "green"
                self.page.update()
                return
            
            if not self.has_permission_handler:
                self.add_log("❌ Permission handler not available", "red")
                self.status_text.value = "❌ Install flet-permission-handler"
                self.status_text.color = "red"
                self.page.update()
                return
            
            self.add_log("Checking STORAGE permission...", "cyan")
            status = await self.permission_handler.check_permission(
                self.fph.PermissionType.STORAGE
            )
            
            self.add_log(f"Status: {status}", "yellow")
            
            if status == self.fph.PermissionStatus.GRANTED:
                self.add_log("✅ STORAGE permission GRANTED", "green")
                self.storage_granted = True
                self.status_text.value = "✅ Storage Permission Granted"
                self.status_text.color = "green"
            elif status == self.fph.PermissionStatus.DENIED:
                self.add_log("⚠️ STORAGE permission DENIED", "orange")
                self.storage_granted = False
                self.status_text.value = "⚠️ Storage Permission Denied"
                self.status_text.color = "orange"
            elif status == self.fph.PermissionStatus.PERMANENTLY_DENIED:
                self.add_log("🚫 STORAGE permission PERMANENTLY DENIED", "red")
                self.storage_granted = False
                self.status_text.value = "🚫 Permission Permanently Denied"
                self.status_text.color = "red"
            else:
                self.add_log(f"❓ Unknown status: {status}", "orange")
                self.storage_granted = False
                self.status_text.value = "❓ Unknown Permission Status"
                self.status_text.color = "orange"
            
            self.page.update()
            
        except Exception as e:
            self.add_log(f"❌ Error: {str(e)}", "red")
            self.status_text.value = "❌ Error checking permission"
            self.status_text.color = "red"
            self.page.update()
    
    async def request_storage_permission(self, e):
        """Request storage permission"""
        try:
            self.add_log("=" * 50, "cyan")
            self.add_log("REQUESTING STORAGE PERMISSION", "yellow")
            
            if not IS_ANDROID:
                self.add_log("Not Android - no request needed", "green")
                return
            
            if not self.has_permission_handler:
                self.add_log("❌ Permission handler not available", "red")
                return
            
            self.add_log("Requesting STORAGE permission...", "cyan")
            result = await self.permission_handler.request_permission(
                self.fph.PermissionType.STORAGE
            )
            
            self.add_log(f"Result: {result}", "yellow")
            
            if result == self.fph.PermissionStatus.GRANTED:
                self.add_log("✅ Permission GRANTED by user", "green")
                self.storage_granted = True
                self.status_text.value = "✅ Permission Granted!"
                self.status_text.color = "green"
            else:
                self.add_log("❌ Permission DENIED by user", "red")
                self.storage_granted = False
                self.status_text.value = "❌ Permission Denied"
                self.status_text.color = "red"
            
            self.page.update()
            
        except Exception as e:
            self.add_log(f"❌ Error: {str(e)}", "red")
            self.status_text.value = "❌ Error requesting permission"
            self.status_text.color = "red"
            self.page.update()
    
    async def test_file_write(self, e):
        """Test file write capability"""
        try:
            self.add_log("=" * 50, "cyan")
            self.add_log("TESTING FILE WRITE", "yellow")
            
            test_dir = tempfile.gettempdir()
            test_file = os.path.join(test_dir, "wallpaper_test.txt")
            
            self.add_log(f"Test directory: {test_dir}", "cyan")
            self.add_log(f"Test file: {test_file}", "cyan")
            
            # Write test
            self.add_log("Writing test file...", "cyan")
            with open(test_file, 'w') as f:
                f.write(f"Test write at {datetime.now()}")
            self.add_log("✅ Write successful", "green")
            
            # Read test
            self.add_log("Reading test file...", "cyan")
            with open(test_file, 'r') as f:
                content = f.read()
            self.add_log(f"✅ Read successful: {content[:30]}", "green")
            
            # Delete test
            self.add_log("Deleting test file...", "cyan")
            os.remove(test_file)
            self.add_log("✅ Delete successful", "green")
            
            self.status_text.value = "✅ File Operations Successful"
            self.status_text.color = "green"
            self.page.update()
            
        except Exception as e:
            self.add_log(f"❌ File operation failed: {str(e)}", "red")
            self.status_text.value = "❌ File Operations Failed"
            self.status_text.color = "red"
            self.page.update()

    def get_test_image(self):
        """Get or download test image"""
        try:
            test_dir = tempfile.gettempdir()
            test_image = os.path.join(test_dir, "wallpaper_test.jpg")
            
            # Check if image already exists
            if os.path.exists(test_image) and os.path.getsize(test_image) > 1000:
                self.add_log(f"✅ استخدام صورة موجودة", "green")
                return test_image
            
            # Look for any existing image files
            self.add_log(f"🔍 البحث عن صور في: {test_dir}", "cyan")
            for file in os.listdir(test_dir):
                if file.endswith(('.jpg', '.jpeg', '.png')):
                    existing_image = os.path.join(test_dir, file)
                    if os.path.getsize(existing_image) > 1000:
                        self.add_log(f"✅ تم العثور على: {file}", "green")
                        return existing_image
            
            # Download sample image
            self.add_log("⬇️ جاري تحميل صورة تجريبية...", "cyan")
            import urllib.request
            
            sample_url = "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=400"
            
            req = urllib.request.Request(sample_url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=15) as response:
                data = response.read()
                with open(test_image, 'wb') as f:
                    f.write(data)
            
            self.add_log(f"✅ تم التحميل: {len(data)} بايت", "green")
            return test_image
            
        except Exception as e:
            self.add_log(f"❌ خطأ في الصورة: {str(e)}", "red")
            return None

    async def method1_direct_bitmap(self, image_path):
        """الطريقة 1: تعيين مباشر باستخدام Bitmap"""
        try:
            self.add_log("--- الطريقة 1: Direct setBitmap ---", "yellow")
            
            from jnius import autoclass, cast
            
            # Get Android classes
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WallpaperManager = autoclass('android.app.WallpaperManager')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            
            # Get context
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', activity.getApplicationContext())
            
            self.add_log("🔄 فك تشفير الصورة...", "cyan")
            bitmap = BitmapFactory.decodeFile(image_path)
            
            if not bitmap:
                raise Exception("فشل فك تشفير الصورة")
            
            self.add_log(f"✅ الصورة: {bitmap.getWidth()}x{bitmap.getHeight()}", "green")
            
            # تعيين الخلفية
            self.add_log("📱 جاري تعيين الخلفية...", "cyan")
            manager = WallpaperManager.getInstance(context)
            manager.setBitmap(bitmap)
            bitmap.recycle()
            
            self.add_log("✅ نجحت الطريقة 1!", "green")
            return True
            
        except Exception as e:
            self.add_log(f"❌ فشلت الطريقة 1: {str(e)}", "red")
            return False

    async def method2_input_stream(self, image_path):
        """الطريقة 2: باستخدام InputStream"""
        try:
            self.add_log("--- الطريقة 2: InputStream ---", "yellow")
            
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WallpaperManager = autoclass('android.app.WallpaperManager')
            FileInputStream = autoclass('java.io.FileInputStream')
            File = autoclass('java.io.File')
            
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', activity.getApplicationContext())
            
            # Create file input stream
            self.add_log("🔄 إنشاء stream...", "cyan")
            file = File(image_path)
            stream = FileInputStream(file)
            
            # Set wallpaper from stream
            self.add_log("📱 تعيين الخلفية من stream...", "cyan")
            manager = WallpaperManager.getInstance(context)
            manager.setStream(stream)
            stream.close()
            
            self.add_log("✅ نجحت الطريقة 2!", "green")
            return True
            
        except Exception as e:
            self.add_log(f"❌ فشلت الطريقة 2: {str(e)}", "red")
            return False

    async def method3_content_uri(self, image_path):
        """الطريقة 3: باستخدام Content URI"""
        try:
            self.add_log("--- الطريقة 3: Content URI ---", "yellow")
            
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WallpaperManager = autoclass('android.app.WallpaperManager')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            File = autoclass('java.io.File')
            Uri = autoclass('android.net.Uri')
            
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', activity.getApplicationContext())
            
            # Create URI
            self.add_log("🔗 إنشاء URI...", "cyan")
            file = File(image_path)
            uri = Uri.fromFile(file)
            
            self.add_log(f"URI: {uri.toString()}", "cyan")
            
            # Open input stream from URI
            self.add_log("🔄 فتح stream من URI...", "cyan")
            resolver = context.getContentResolver()
            stream = resolver.openInputStream(uri)
            
            # Decode bitmap
            bitmap = BitmapFactory.decodeStream(stream)
            stream.close()
            
            if not bitmap:
                raise Exception("فشل فك التشفير من URI")
            
            # Set wallpaper
            self.add_log("📱 تعيين الخلفية...", "cyan")
            manager = WallpaperManager.getInstance(context)
            manager.setBitmap(bitmap)
            bitmap.recycle()
            
            self.add_log("✅ نجحت الطريقة 3!", "green")
            return True
            
        except Exception as e:
            self.add_log(f"❌ فشلت الطريقة 3: {str(e)}", "red")
            return False

    async def method4_with_scaling(self, image_path):
        """الطريقة 4: مع تغيير الحجم"""
        try:
            self.add_log("--- الطريقة 4: With Scaling ---", "yellow")
            
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WallpaperManager = autoclass('android.app.WallpaperManager')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            Options = autoclass('android.graphics.BitmapFactory$Options')
            Bitmap = autoclass('android.graphics.Bitmap')
            Config = autoclass('android.graphics.Bitmap$Config')
            Canvas = autoclass('android.graphics.Canvas')
            Paint = autoclass('android.graphics.Paint')
            
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            context = cast('android.content.Context', activity.getApplicationContext())
            
            # Get screen dimensions
            display = activity.getWindowManager().getDefaultDisplay()
            width = display.getWidth()
            height = display.getHeight()
            self.add_log(f"📱 الشاشة: {width}x{height}", "cyan")
            
            # Decode with bounds first
            self.add_log("🔍 فحص أبعاد الصورة...", "cyan")
            options = Options()
            options.inJustDecodeBounds = True
            BitmapFactory.decodeFile(image_path, options)
            
            img_width = options.outWidth
            img_height = options.outHeight
            self.add_log(f"🖼️ الصورة: {img_width}x{img_height}", "cyan")
            
            # Calculate sample size
            sample_size = 1
            if img_width > width or img_height > height:
                sample_size = max(img_width // width, img_height // height)
            
            self.add_log(f"📏 حجم العينة: {sample_size}", "cyan")
            
            # Decode with sample size
            options.inJustDecodeBounds = False
            options.inSampleSize = sample_size
            bitmap = BitmapFactory.decodeFile(image_path, options)
            
            if not bitmap:
                raise Exception("فشل فك تشفير الصورة")
            
            self.add_log(f"✅ تم الفك: {bitmap.getWidth()}x{bitmap.getHeight()}", "green")
            
            # Set wallpaper
            self.add_log("📱 تعيين الخلفية...", "cyan")
            manager = WallpaperManager.getInstance(context)
            manager.setBitmap(bitmap)
            bitmap.recycle()
            
            self.add_log("✅ نجحت الطريقة 4!", "green")
            return True
            
        except Exception as e:
            self.add_log(f"❌ فشلت الطريقة 4: {str(e)}", "red")
            return False

    async def method5_intent(self, image_path):
        """الطريقة 5: باستخدام Intent (الأكثر موثوقية)"""
        try:
            self.add_log("--- الطريقة 5: Intent ---", "yellow")
            
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            
            activity = cast('android.app.Activity', PythonActivity.mActivity)
            
            # Create URI
            file = File(image_path)
            uri = Uri.fromFile(file)
            
            # Create intent
            self.add_log("📲 إنشاء Intent للخلفية...", "cyan")
            intent = Intent(Intent.ACTION_ATTACH_DATA)
            intent.setDataAndType(uri, "image/*")
            intent.putExtra("mimeType", "image/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            
            # Start chooser
            self.add_log("🚀 فتح قائمة الاختيار...", "cyan")
            chooser = Intent.createChooser(intent, "تعيين كخلفية")
            activity.startActivity(chooser)
            
            self.add_log("✅ تم إرسال Intent!", "green")
            self.add_log("⚠️ اختر 'خلفية الشاشة' من القائمة", "yellow")
            return True
            
        except Exception as e:
            self.add_log(f"❌ فشلت الطريقة 5: {str(e)}", "red")
            return False
    
    async def test_set_wallpaper(self, e):
        """تجربة جميع الطرق تلقائياً"""
        try:
            self.add_log("=" * 50, "cyan")
            self.add_log("🔄 تجربة جميع الطرق تلقائياً", "yellow")
            
            if not IS_ANDROID:
                self.add_log("❌ يعمل فقط على أندرويد", "red")
                self.status_text.value = "❌ أندرويد فقط"
                self.status_text.color = "red"
                self.page.update()
                return
            
            # Get test image
            image_path = self.get_test_image()
            if not image_path:
                self.add_log("❌ لا توجد صورة اختبار", "red")
                self.status_text.value = "❌ لا توجد صورة"
                self.status_text.color = "red"
                self.page.update()
                return
            
            # Verify file
            if not os.path.exists(image_path):
                self.add_log("❌ الصورة غير موجودة", "red")
                self.status_text.value = "❌ الصورة غير موجودة"
                self.status_text.color = "red"
                self.page.update()
                return
            
            file_size = os.path.getsize(image_path) / 1024
            self.add_log(f"📁 الصورة: {file_size:.1f} كيلوبايت", "cyan")
            self.add_log(f"📂 المسار: {image_path}", "cyan")
            
            # Try methods in order
            methods = [
                ("الطريقة 1: Direct Bitmap", self.method1_direct_bitmap),
                ("الطريقة 2: Input Stream", self.method2_input_stream),
                ("الطريقة 3: Content URI", self.method3_content_uri),
                ("الطريقة 4: With Scaling", self.method4_with_scaling),
                ("الطريقة 5: Intent", self.method5_intent),
            ]
            
            for method_name, method_func in methods:
                self.add_log(f"\n🔄 جاري تجربة {method_name}...", "cyan")
                success = await method_func(image_path)
                
                if success:
                    self.add_log(f"\n🎉 {method_name} نجحت!", "green")
                    self.status_text.value = f"✅ نجح: {method_name}"
                    self.status_text.color = "green"
                    self.page.update()
                    return
                
                # Small delay between methods
                import asyncio
                await asyncio.sleep(0.5)
            
            # If all failed
            self.add_log("\n❌ فشلت جميع الطرق", "red")
            self.status_text.value = "❌ فشلت جميع الطرق"
            self.status_text.color = "red"
            self.page.update()
            
        except Exception as e:
            self.add_log(f"❌ خطأ كبير: {str(e)}", "red")
            import traceback
            tb = traceback.format_exc()
            for line in tb.split('\n')[:5]:
                if line.strip():
                    self.add_log(line[:100], "red")
            self.status_text.value = "❌ خطأ كبير"
            self.status_text.color = "red"
            self.page.update()
    
    async def open_settings(self, e):
        """فتح إعدادات التطبيق"""
        try:
            self.add_log("=" * 50, "cyan")
            self.add_log("⚙️ فتح الإعدادات", "yellow")
            
            if not IS_ANDROID:
                self.add_log("❌ ليس أندرويد", "red")
                return
            
            if self.has_permission_handler:
                success = await self.permission_handler.open_app_settings()
                if success:
                    self.add_log("✅ تم فتح الإعدادات", "green")
                else:
                    self.add_log("❌ فشل فتح الإعدادات", "red")
            else:
                self.add_log("❌ معالج الأذونات غير متوفر", "red")
            
        except Exception as e:
            self.add_log(f"❌ خطأ: {str(e)}", "red")
    
    def clear_logs(self, e):
        """مسح جميع السجلات"""
        self.logs.clear()
        self.log_container.controls.clear()
        self.add_log("تم مسح السجلات ✓", "cyan")
        self.status_text.value = "جاهز لتجربة الطرق"
        self.status_text.color = "white"
        self.page.update()
    
    def build(self):
        """Build UI"""
        
        # Add permission handler to overlay if available
        if self.permission_handler:
            self.page.overlay.append(self.permission_handler)
            print("✓ Permission handler added to overlay")
        
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.SECURITY, size=40, color=ft.Colors.CYAN_400),
                            ft.Column([
                                ft.Text("اختبار الخلفيات", size=28, weight=ft.FontWeight.BOLD),
                                ft.Text(f"المنصة: {'أندرويد' if IS_ANDROID else 'سطح المكتب'}", size=12, color=ft.Colors.GREY_400),
                            ], spacing=2),
                        ], spacing=15),
                        ft.Container(height=10),
                        self.status_text,
                    ], spacing=5),
                    padding=20,
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    border_radius=10,
                ),
                
                ft.Container(height=10),
                
                # Control Buttons
                ft.Container(
                    content=ft.Column([
                        ft.Text("طرق تعيين الخلفية - Wallpaper Methods", size=16, weight=ft.FontWeight.BOLD),
                        
                        ft.ElevatedButton(
                            "الطريقة 1: Direct Bitmap",
                            icon=ft.Icons.IMAGE,
                            on_click=lambda e: self.run_single_method(e, 1),
                            width=300,
                            bgcolor=ft.Colors.BLUE_700,
                        ),
                        
                        ft.ElevatedButton(
                            "الطريقة 2: Input Stream",
                            icon=ft.Icons.STREAM,
                            on_click=lambda e: self.run_single_method(e, 2),
                            width=300,
                            bgcolor=ft.Colors.GREEN_700,
                        ),
                        
                        ft.ElevatedButton(
                            "الطريقة 3: Content URI",
                            icon=ft.Icons.LINK,
                            on_click=lambda e: self.run_single_method(e, 3),
                            width=300,
                            bgcolor=ft.Colors.ORANGE_700,
                        ),
                        
                        ft.ElevatedButton(
                            "الطريقة 4: With Scaling",
                            icon=ft.Icons.PHOTO_SIZE_SELECT_LARGE,
                            on_click=lambda e: self.run_single_method(e, 4),
                            width=300,
                            bgcolor=ft.Colors.PURPLE_700,
                        ),
                        
                        ft.ElevatedButton(
                            "الطريقة 5: Intent (موصى بها)",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e: self.run_single_method(e, 5),
                            width=300,
                            bgcolor=ft.Colors.RED_700,
                        ),
                        
                        ft.Divider(height=20),
                        
                        ft.ElevatedButton(
                            "🔄 جرب كل الطرق تلقائياً",
                            icon=ft.Icons.AUTORENEW,
                            on_click=self.test_set_wallpaper,
                            width=300,
                            bgcolor=ft.Colors.CYAN_700,
                        ),
                        
                        ft.Divider(height=20),
                        
                        ft.Row([
                            ft.ElevatedButton(
                                "⚙️ الإعدادات",
                                icon=ft.Icons.SETTINGS,
                                on_click=self.open_settings,
                            ),
                            ft.ElevatedButton(
                                "🗑️ مسح السجل",
                                icon=ft.Icons.CLEAR,
                                on_click=self.clear_logs,
                            ),
                        ], spacing=10),
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    border_radius=10,
                ),
                
                ft.Container(height=10),
                
                # Log Container
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.TERMINAL, size=20),
                            ft.Text("سجل النشاط - Activity Log", size=16, weight=ft.FontWeight.BOLD),
                        ], spacing=10),
                        ft.Divider(height=1),
                        self.log_container,
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    border_radius=10,
                    expand=True,
                ),
                
            ], spacing=10, expand=True, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True,
        )

def main(page: ft.Page):
    page.title = "اختبار الخلفيات - Wallpaper Test"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#0a0e1a"
    
    app = PermissionTestApp(page)
    page.add(app.build())
    
    # Add initial log
    app.add_log("✅ تم بدء التطبيق بنجاح", "green")
    app.add_log(f"📱 المنصة: {'أندرويد' if IS_ANDROID else 'سطح المكتب'}", "cyan")
    app.add_log(f"🔧 معالج الأذونات: {'متوفر' if app.has_permission_handler else 'غير مثبت'}", 
                "green" if app.has_permission_handler else "orange")

if __name__ == "__main__":
    ft.app(target=main)