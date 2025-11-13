import flet as ft
from flet_ads import BannerAd, InterstitialAd


def main(page: ft.Page):
    page.title = "AdMob Test App"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Determine platform for correct test ad unit IDs
    is_android = page.platform == ft.PagePlatform.ANDROID
    
    # Test Ad Unit IDs based on platform (correct IDs from documentation)
    banner_unit_id = (
        "ca-app-pub-3940256099942544/6300978111" if is_android 
        else "ca-app-pub-3940256099942544/2934735716"
    )
    interstitial_unit_id = (
        "ca-app-pub-3940256099942544/1033173712" if is_android
        else "ca-app-pub-3940256099942544/4411468910"
    )

    # Status text with detailed logging
    status_text = ft.Text("Ready to test ads", size=16, weight=ft.FontWeight.BOLD)
    error_log = ft.Text("", size=12, color=ft.Colors.RED_700)
    
    def log_status(message, is_error=False):
        """Helper function to log status messages"""
        status_text.value = message
        if is_error:
            error_log.value = message
        print(f"[AdMob] {message}")  # Console logging
        page.update()

    # Create Banner Ad (NO size parameter!)
    try:
        banner_ad = BannerAd(
            unit_id=banner_unit_id,
        )
    except Exception as e:
        log_status(f"❌ Failed to create Banner Ad: {str(e)}", True)
        banner_ad = None

    # Create Interstitial Ad
    try:
        interstitial_ad = InterstitialAd(
            unit_id=interstitial_unit_id,
        )
    except Exception as e:
        log_status(f"❌ Failed to create Interstitial Ad: {str(e)}", True)
        interstitial_ad = None

    # Event handlers with detailed error information
    def on_banner_loaded(e):
        log_status("✅ Banner Ad Loaded Successfully!")

    def on_banner_failed(e):
        error_details = e.data if hasattr(e, 'data') else str(e)
        log_status(f"❌ Banner Ad Failed: {error_details}", True)

    def on_banner_clicked(e):
        log_status("👆 Banner Ad Clicked")

    def on_banner_impression(e):
        log_status("👁️ Banner Ad Impression Recorded")

    def on_banner_opened(e):
        log_status("📖 Banner Ad Opened")

    def on_banner_closed(e):
        log_status("📕 Banner Ad Closed")

    def on_banner_will_dismiss(e):
        log_status("⚠️ Banner Ad Will Dismiss (iOS only)")

    def on_interstitial_loaded(e):
        log_status("✅ Interstitial Ad Loaded! Ready to show.")
        show_interstitial_btn.disabled = False
        page.update()

    def on_interstitial_failed(e):
        error_details = e.data if hasattr(e, 'data') else str(e)
        log_status(f"❌ Interstitial Ad Failed: {error_details}", True)
        show_interstitial_btn.disabled = True
        page.update()

    def on_interstitial_opened(e):
        log_status("📺 Interstitial Ad Opened")

    def on_interstitial_closed(e):
        log_status("👋 Interstitial Ad Closed")
        show_interstitial_btn.disabled = True
        # Remove old ad and create new one
        if interstitial_ad:
            page.overlay.remove(interstitial_ad)
            new_ad = InterstitialAd(unit_id=interstitial_unit_id)
            new_ad.on_load = on_interstitial_loaded
            new_ad.on_error = on_interstitial_failed
            new_ad.on_open = on_interstitial_opened
            new_ad.on_close = on_interstitial_closed
            new_ad.on_click = on_interstitial_clicked
            new_ad.on_impression = on_interstitial_impression
            page.overlay.append(new_ad)
        page.update()

    def on_interstitial_clicked(e):
        log_status("👆 Interstitial Ad Clicked")

    def on_interstitial_impression(e):
        log_status("👁️ Interstitial Ad Impression Recorded")

    # Set up event handlers with null checks
    if banner_ad:
        banner_ad.on_load = on_banner_loaded
        banner_ad.on_error = on_banner_failed
        banner_ad.on_click = on_banner_clicked
        banner_ad.on_impression = on_banner_impression
        banner_ad.on_open = on_banner_opened
        banner_ad.on_close = on_banner_closed
        banner_ad.on_will_dismiss = on_banner_will_dismiss
    
    if interstitial_ad:
        interstitial_ad.on_load = on_interstitial_loaded
        interstitial_ad.on_error = on_interstitial_failed
        interstitial_ad.on_open = on_interstitial_opened
        interstitial_ad.on_close = on_interstitial_closed
        interstitial_ad.on_click = on_interstitial_clicked
        interstitial_ad.on_impression = on_interstitial_impression
        # Add to overlay for interstitial ads
        page.overlay.append(interstitial_ad)

    # Load Banner Ad
    def load_banner(e):
        if not banner_ad:
            log_status("❌ Banner Ad not initialized", True)
            return
        
        try:
            log_status("⏳ Loading Banner Ad...")
            banner_ad.load()
        except Exception as ex:
            log_status(f"❌ Error loading Banner Ad: {str(ex)}", True)

    # Load Interstitial Ad
    def load_interstitial(e):
        if not interstitial_ad:
            log_status("❌ Interstitial Ad not initialized", True)
            return
        
        try:
            log_status("⏳ Loading Interstitial Ad...")
            show_interstitial_btn.disabled = True
            page.update()
            interstitial_ad.load()
        except Exception as ex:
            log_status(f"❌ Error loading Interstitial Ad: {str(ex)}", True)
            show_interstitial_btn.disabled = True
            page.update()

    # Show Interstitial Ad
    def show_interstitial(e):
        if not interstitial_ad:
            log_status("❌ Interstitial Ad not initialized", True)
            return
        
        try:
            interstitial_ad.show()
        except Exception as ex:
            log_status(f"❌ Error showing Interstitial Ad: {str(ex)}", True)

    # Buttons
    load_banner_btn = ft.ElevatedButton(
        "Load Banner Ad",
        icon=ft.Icons.AD_UNITS,
        on_click=load_banner,
        disabled=banner_ad is None,
    )

    load_interstitial_btn = ft.ElevatedButton(
        "Load Interstitial Ad",
        icon=ft.Icons.FULLSCREEN,
        on_click=load_interstitial,
        disabled=interstitial_ad is None,
    )

    show_interstitial_btn = ft.ElevatedButton(
        "Show Interstitial Ad",
        icon=ft.Icons.PLAY_ARROW,
        on_click=show_interstitial,
        disabled=True,
    )

    # Platform info
    platform_info = ft.Text(
        f"Platform: {page.platform.value if page.platform else 'Unknown'}\n"
        f"Banner ID: {banner_unit_id}\n"
        f"Interstitial ID: {interstitial_unit_id}",
        size=12,
        color=ft.Colors.GREY_700,
    )

    # Layout
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("🎯 AdMob Test App", size=28, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    platform_info,
                    ft.Divider(),
                    status_text,
                    error_log,
                    ft.Container(height=20),
                    ft.Text("Banner Ad Controls:", size=18, weight=ft.FontWeight.BOLD),
                    load_banner_btn,
                    # Banner ad MUST be in a Container with fixed width/height
                    ft.Container(
                        content=banner_ad if banner_ad else ft.Text("Banner Ad unavailable"),
                        width=320,  # Standard banner width
                        height=50,  # Standard banner height
                        alignment=ft.alignment.center,
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_400),
                        border_radius=10,
                        bgcolor=ft.Colors.TRANSPARENT,
                    ),
                    ft.Container(height=20),
                    ft.Text("Interstitial Ad Controls:", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([load_interstitial_btn, show_interstitial_btn]),
                    ft.Container(height=20),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("📝 Test Instructions:", weight=ft.FontWeight.BOLD),
                                ft.Text("1. Click 'Load Banner Ad' to load and display banner"),
                                ft.Text("2. Click 'Load Interstitial Ad' to prepare full-screen ad"),
                                ft.Text("3. Click 'Show Interstitial Ad' once loaded"),
                                ft.Text("4. These are test ads from Google AdMob"),
                                ft.Divider(),
                                ft.Text("⚠️ Common Android Issues:", weight=ft.FontWeight.BOLD),
                                ft.Text("• Add AdMob App ID to pyproject.toml or build command"),
                                ft.Text("• Check internet permission in AndroidManifest.xml"),
                                ft.Text("• Ensure flet-ads is in dependencies"),
                                ft.Text("• Use --include-packages flet_ads when building"),
                                ft.Text("• Banner ads need fixed width/height container"),
                            ]),
                            padding=15,
                        )
                    ),
                ],
                spacing=10,
            ),
            padding=20,
        )
    )


ft.app(target=main)