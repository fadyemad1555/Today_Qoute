import flet as ft
import random

# Check if we're on a mobile platform
def is_mobile_platform(page):
    if not page.platform:
        return False
    return page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

# Mock Ad classes for desktop testing
class MockBannerAd(ft.Container):
    def __init__(self, unit_id, **kwargs):
        super().__init__(**kwargs)
        self.unit_id = unit_id
        self.on_load = None
        self.on_error = None
        self.on_click = None
        self.on_impression = None
        self.on_open = None
        self.on_close = None
        self.on_will_dismiss = None
        self._loaded = False
        
        # Create mock ad visual
        self.content = ft.Column([
            ft.Text("🎯 MOCK BANNER AD", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text("(Desktop Simulator)", size=10, color=ft.Colors.WHITE70),
            ft.Text("Click to simulate interaction", size=9, color=ft.Colors.WHITE60),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.bgcolor = ft.Colors.BLUE_700
        self.border_radius = 5
        self.padding = 5
        self.ink = True
        self.on_click = self._handle_click
        
    def load(self):
        """Simulate loading an ad"""
        import threading
        def delayed_load():
            import time
            time.sleep(1)  # Simulate network delay
            self._loaded = True
            if self.on_load:
                self.on_load(type('Event', (), {'data': 'loaded'})())
            # Simulate impression
            time.sleep(0.5)
            if self.on_impression:
                self.on_impression(type('Event', (), {'data': 'impression'})())
        
        threading.Thread(target=delayed_load, daemon=True).start()
    
    def _handle_click(self, e):
        if self._loaded and self.on_click:
            self.on_click(type('Event', (), {'data': 'clicked'})())

class MockInterstitialAd:
    def __init__(self, unit_id, **kwargs):
        self.unit_id = unit_id
        self.on_load = None
        self.on_error = None
        self.on_click = None
        self.on_impression = None
        self.on_open = None
        self.on_close = None
        self._loaded = False
        self._page = None
        self._dialog = None
        
    def load(self):
        """Simulate loading an interstitial ad"""
        import threading
        def delayed_load():
            import time
            time.sleep(1.5)  # Simulate network delay
            self._loaded = True
            if self.on_load:
                self.on_load(type('Event', (), {'data': 'loaded'})())
        
        threading.Thread(target=delayed_load, daemon=True).start()
    
    def show(self):
        """Show the mock interstitial ad"""
        if not self._loaded:
            return
        
        if self.on_open:
            self.on_open(type('Event', (), {'data': 'opened'})())
        
        # Create and show dialog
        def close_dialog(e):
            if self._dialog and self._page:
                self._dialog.open = False
                self._page.update()
                if self.on_close:
                    self.on_close(type('Event', (), {'data': 'closed'})())
                self._loaded = False
        
        def click_ad(e):
            if self.on_click:
                self.on_click(type('Event', (), {'data': 'clicked'})())
        
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("🎯 MOCK INTERSTITIAL AD", text_align=ft.TextAlign.CENTER),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("This is a simulated full-screen ad", text_align=ft.TextAlign.CENTER),
                    ft.Text("(Desktop Simulator Only)", size=12, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=20),
                    ft.Image(
                        src="https://via.placeholder.com/300x250.png?text=Sample+Ad",
                        width=300,
                        height=250,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "Simulate Ad Click",
                        icon=ft.Icons.ADS_CLICK,
                        on_click=click_ad,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
            ),
            actions=[
                ft.TextButton("Close Ad", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        
        # Record impression
        if self.on_impression:
            self.on_impression(type('Event', (), {'data': 'impression'})())


def main(page: ft.Page):
    page.title = "AdMob Test App (Cross-Platform)"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Platform detection
    platform = page.platform if page.platform else ft.PagePlatform.LINUX
    is_mobile = is_mobile_platform(page)
    
    # Test Ad Unit IDs
    is_android = platform == ft.PagePlatform.ANDROID
    banner_unit_id = (
        "ca-app-pub-3940256099942544/6300978111" if is_android 
        else "ca-app-pub-3940256099942544/2934735716"
    )
    interstitial_unit_id = (
        "ca-app-pub-3940256099942544/1033173712" if is_android
        else "ca-app-pub-3940256099942544/4411468910"
    )

    # Status and logging
    status_text = ft.Text("Ready to test ads", size=16, weight=ft.FontWeight.BOLD)
    error_log = ft.Text("", size=12, color=ft.Colors.RED_700)
    event_log = ft.Column([], scroll=ft.ScrollMode.AUTO, height=200)
    
    def log_status(message, is_error=False):
        """Enhanced logging with event history"""
        status_text.value = message
        if is_error:
            error_log.value = message
        
        # Add to event log
        timestamp = ft.Text(
            f"[{len(event_log.controls)}] {message}",
            size=11,
            color=ft.Colors.RED_700 if is_error else ft.Colors.BLUE_700
        )
        event_log.controls.insert(0, timestamp)
        if len(event_log.controls) > 20:
            event_log.controls.pop()
        
        print(f"[AdMob] {message}")
        page.update()

    # Initialize ads based on platform
    banner_ad = None
    interstitial_ad = None
    
    if is_mobile:
        try:
            from flet_ads import BannerAd, InterstitialAd
            banner_ad = BannerAd(unit_id=banner_unit_id)
            interstitial_ad = InterstitialAd(unit_id=interstitial_unit_id)
            log_status(f"✅ Real AdMob ads initialized for {platform.value}")
        except Exception as e:
            log_status(f"❌ Failed to create real ads: {str(e)}", True)
            # Fall back to mock
            banner_ad = MockBannerAd(unit_id=banner_unit_id, width=320, height=50)
            interstitial_ad = MockInterstitialAd(unit_id=interstitial_unit_id)
            log_status("⚠️ Using mock ads as fallback")
    else:
        # Desktop: Use mock ads
        log_status(f"🖥️ Desktop platform detected ({platform.value})")
        log_status("📱 Using MOCK ads for development (real ads require mobile)")
        banner_ad = MockBannerAd(unit_id=banner_unit_id, width=320, height=50)
        interstitial_ad = MockInterstitialAd(unit_id=interstitial_unit_id)
        interstitial_ad._page = page

    # Event handlers
    def on_banner_loaded(e):
        log_status("✅ Banner Ad Loaded Successfully!")

    def on_banner_failed(e):
        error_details = getattr(e, 'data', str(e))
        log_status(f"❌ Banner Ad Failed: {error_details}", True)

    def on_banner_clicked(e):
        log_status("👆 Banner Ad Clicked")

    def on_banner_impression(e):
        log_status("👁️ Banner Ad Impression Recorded")

    def on_banner_opened(e):
        log_status("📖 Banner Ad Opened")

    def on_banner_closed(e):
        log_status("📕 Banner Ad Closed")

    def on_interstitial_loaded(e):
        log_status("✅ Interstitial Ad Loaded! Ready to show.")
        show_interstitial_btn.disabled = False
        page.update()

    def on_interstitial_failed(e):
        error_details = getattr(e, 'data', str(e))
        log_status(f"❌ Interstitial Ad Failed: {error_details}", True)
        load_interstitial_btn.disabled = False
        page.update()

    def on_interstitial_opened(e):
        log_status("📺 Interstitial Ad Opened")

    def on_interstitial_closed(e):
        log_status("👋 Interstitial Ad Closed")
        show_interstitial_btn.disabled = True
        load_interstitial_btn.disabled = False
        page.update()

    def on_interstitial_clicked(e):
        log_status("👆 Interstitial Ad Clicked")

    def on_interstitial_impression(e):
        log_status("👁️ Interstitial Ad Impression Recorded")

    # Attach event handlers
    if banner_ad:
        banner_ad.on_load = on_banner_loaded
        banner_ad.on_error = on_banner_failed
        banner_ad.on_click = on_banner_clicked
        banner_ad.on_impression = on_banner_impression
        banner_ad.on_open = on_banner_opened
        banner_ad.on_close = on_banner_closed
    
    if interstitial_ad:
        interstitial_ad.on_load = on_interstitial_loaded
        interstitial_ad.on_error = on_interstitial_failed
        interstitial_ad.on_open = on_interstitial_opened
        interstitial_ad.on_close = on_interstitial_closed
        interstitial_ad.on_click = on_interstitial_clicked
        interstitial_ad.on_impression = on_interstitial_impression
        
        # Add to overlay only for real ads
        if is_mobile:
            page.overlay.append(interstitial_ad)

    # Button handlers
    def load_banner(e):
        try:
            log_status("⏳ Loading Banner Ad...")
            load_banner_btn.disabled = True
            page.update()
            banner_ad.load()
            load_banner_btn.disabled = False
            page.update()
        except Exception as ex:
            log_status(f"❌ Error loading Banner Ad: {str(ex)}", True)
            load_banner_btn.disabled = False
            page.update()

    def load_interstitial(e):
        try:
            log_status("⏳ Loading Interstitial Ad...")
            load_interstitial_btn.disabled = True
            show_interstitial_btn.disabled = True
            page.update()
            interstitial_ad.load()
        except Exception as ex:
            log_status(f"❌ Error loading Interstitial Ad: {str(ex)}", True)
            load_interstitial_btn.disabled = False
            page.update()

    def show_interstitial(e):
        try:
            log_status("📺 Showing Interstitial Ad...")
            interstitial_ad.show()
        except Exception as ex:
            log_status(f"❌ Error showing Interstitial Ad: {str(ex)}", True)

    def clear_logs(e):
        event_log.controls.clear()
        error_log.value = ""
        status_text.value = "Logs cleared"
        page.update()

    # UI Components
    load_banner_btn = ft.ElevatedButton(
        "Load Banner Ad",
        icon=ft.Icons.AD_UNITS,
        on_click=load_banner,
    )

    load_interstitial_btn = ft.ElevatedButton(
        "Load Interstitial Ad",
        icon=ft.Icons.FULLSCREEN,
        on_click=load_interstitial,
    )

    show_interstitial_btn = ft.ElevatedButton(
        "Show Interstitial Ad",
        icon=ft.Icons.PLAY_ARROW,
        on_click=show_interstitial,
        disabled=True,
    )

    clear_logs_btn = ft.TextButton(
        "Clear Logs",
        icon=ft.Icons.CLEAR_ALL,
        on_click=clear_logs,
    )

    # Platform info
    mode_text = "REAL ADS MODE 📱" if is_mobile else "MOCK/SIMULATOR MODE 🖥️"
    mode_color = ft.Colors.GREEN_700 if is_mobile else ft.Colors.ORANGE_700
    
    platform_info = ft.Container(
        content=ft.Column([
            ft.Text(mode_text, weight=ft.FontWeight.BOLD, size=16, color=mode_color),
            ft.Divider(height=10),
            ft.Text(f"Platform: {platform.value if platform else 'Unknown'}"),
            ft.Text(f"Is Mobile: {'Yes ✅' if is_mobile else 'No ❌'}"),
            ft.Text(f"Banner ID: {banner_unit_id}", size=10),
            ft.Text(f"Interstitial ID: {interstitial_unit_id}", size=10),
        ]),
        padding=10,
        border=ft.border.all(2, mode_color),
        border_radius=5,
        bgcolor=ft.Colors.GREEN_50 if is_mobile else ft.Colors.ORANGE_50,
    )

    # Mode explanation
    mode_explanation = None
    if not is_mobile:
        mode_explanation = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE_700, size=30),
                ft.Text(
                    "Desktop Simulator Mode",
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_900,
                    size=16
                ),
                ft.Text(
                    "You're testing with MOCK ads that simulate AdMob behavior.",
                    size=12,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "• All ad events work (load, show, click, impression)",
                    size=11,
                ),
                ft.Text(
                    "• Perfect for UI development and testing logic",
                    size=11,
                ),
                ft.Text(
                    "• No real ads will display on desktop",
                    size=11,
                ),
                ft.Divider(),
                ft.Text(
                    "📱 To test REAL ads:",
                    weight=ft.FontWeight.BOLD,
                    size=12
                ),
                ft.Text(
                    "Build for mobile: flet build apk or flet build ipa",
                    size=11,
                    italic=True,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            border=ft.border.all(2, ft.Colors.BLUE_700),
            border_radius=10,
            bgcolor=ft.Colors.BLUE_50,
        )

    # Instructions
    instructions = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("📝 Testing Instructions:", weight=ft.FontWeight.BOLD),
                ft.Text("1. Click 'Load Banner Ad' to load banner"),
                ft.Text("2. Click 'Load Interstitial Ad' to prepare full-screen ad"),
                ft.Text("3. Click 'Show Interstitial Ad' once loaded"),
                ft.Text("4. Watch the event log for all ad events"),
                ft.Divider(),
                ft.Text("🔧 For Mobile Deployment:", weight=ft.FontWeight.BOLD),
                ft.Text("• pip install flet flet-ads"),
                ft.Text("• Add flet-ads to pyproject.toml dependencies"),
                ft.Text("• Configure AdMob App ID in your project"),
                ft.Text("• Build: flet build apk --include-packages flet_ads"),
                ft.Text("• Test on real device or emulator"),
            ]),
            padding=15,
        )
    )

    # Layout
    controls = [
        ft.Text("🎯 AdMob Test App", size=28, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        platform_info,
    ]
    
    if mode_explanation:
        controls.append(mode_explanation)
    
    controls.extend([
        ft.Divider(),
        status_text,
        error_log,
        ft.Container(height=10),
        ft.Text("Event Log:", size=14, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=event_log,
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=5,
            padding=5,
        ),
        clear_logs_btn,
        ft.Container(height=10),
        ft.Text("Banner Ad Controls:", size=18, weight=ft.FontWeight.BOLD),
        load_banner_btn,
        ft.Container(
            content=banner_ad,
            alignment=ft.alignment.center,
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=10,
            bgcolor=ft.Colors.GREY_100,
        ),
        ft.Container(height=10),
        ft.Text("Interstitial Ad Controls:", size=18, weight=ft.FontWeight.BOLD),
        ft.Row([load_interstitial_btn, show_interstitial_btn], spacing=10),
        ft.Container(height=10),
        instructions,
    ])

    page.add(
        ft.Container(
            content=ft.Column(controls, spacing=10),
            padding=20,
        )
    )


if __name__ == "__main__":
    ft.app(target=main)