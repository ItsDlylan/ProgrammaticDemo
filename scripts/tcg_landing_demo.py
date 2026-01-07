#!/usr/bin/env python3
"""
TCG Elevate Landing Page Demo Recording Script

This script creates a smooth, cinematic recording of the TCG Elevate landing page,
showcasing all sections, animations, and interactive elements.

Page Structure (total height: ~9838px):
1. Hero Section (0-800px) - Title with gradient text, CTAs
2. Feature Icons (800-1500px) - Animated expanding icons
3. Badge Pills Section (1500-2600px) - Colorful feature badges
4. Pain Points (2600-3800px) - "Sound Familiar?" problem cards
5. Card Search Demo (3800-4800px) - Animated Charizard search
6. Workflow Steps (4800-6800px) - Organize → Trade → Track
7. FAQ Section (6800-7800px) - Expandable accordions
8. Pricing Section (7800-8900px) - 3-tier pricing cards
9. Final CTA + Footer (8900-9838px) - Stats and waitlist
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import math


class LandingPageDemo:
    """Orchestrates a smooth demo recording of the TCG Elevate landing page."""

    def __init__(self, url: str, output_dir: str = "./recordings"):
        self.url = url
        self.output_dir = output_dir
        self.browser = None
        self.page = None
        self.context = None

        # Viewport settings for high-quality recording
        self.viewport = {"width": 1280, "height": 800}

        # Scroll configuration
        self.scroll_speed = 1.5  # pixels per frame at 60fps
        self.pause_duration = 2.0  # seconds to pause at key sections

        # Key waypoints (scroll positions) with pause durations
        # scroll_duration controls how long to take scrolling TO this position (slower = more cinematic)
        self.waypoints = [
            {"name": "hero", "position": 0, "pause": 3.0, "scroll_duration": 1.5, "description": "Hero section with gradient title"},
            {"name": "badges_end", "position": 2050, "pause": 1.5, "scroll_duration": 8.0, "description": "Continuous scroll through icons & badges animation"},
            # Reality Check: header at top, full 6-card grid visible
            {"name": "reality_check", "position": 3025, "pause": 3.5, "scroll_duration": 2.0, "description": "Reality Check header + full card grid"},
            # Card Search: header visible with full search component and results
            {"name": "card_search", "position": 4075, "pause": 5.0, "scroll_duration": 2.0, "description": "Find Any Card - full search demo"},
            # Workflow: header + Step 1 centered
            {"name": "workflow_step1", "position": 4950, "pause": 3.0, "scroll_duration": 2.0, "description": "See How Your Business Transforms + Step 1 centered"},
            # Each step centered on screen
            {"name": "step2_trade", "position": 5650, "pause": 2.5, "scroll_duration": 1.5, "description": "Step 2: Trade - centered"},
            {"name": "step3_track", "position": 6250, "pause": 3.0, "scroll_duration": 1.5, "description": "Step 3: Track - centered"},
            # FAQ: header at top of viewport
            {"name": "faq", "position": 7250, "pause": 2.5, "scroll_duration": 2.0, "description": "FAQ header at top"},
            # Pricing: header visible with all 3 cards
            {"name": "pricing", "position": 8100, "pause": 3.5, "scroll_duration": 2.5, "description": "Pricing header + all 3 tiers"},
            # Final CTA with stats and footer
            {"name": "final_cta", "position": 9038, "pause": 3.0, "scroll_duration": 2.5, "description": "Final CTA with stats"},
        ]

    async def setup(self):
        """Initialize browser and page with recording capabilities."""
        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=False,  # Show browser for visual feedback
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )

        # Create context with video recording
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.context = await self.browser.new_context(
            viewport=self.viewport,
            record_video_dir=self.output_dir,
            record_video_size=self.viewport
        )

        self.page = await self.context.new_page()

        # Set up smooth scrolling behavior
        await self.page.add_init_script("""
            document.documentElement.style.scrollBehavior = 'auto';
        """)

        print(f"Browser initialized with viewport {self.viewport['width']}x{self.viewport['height']}")

    async def navigate(self):
        """Navigate to the landing page and wait for full load."""
        print(f"Navigating to {self.url}...")
        try:
            await self.page.goto(self.url, wait_until="load", timeout=60000)
        except Exception as e:
            print(f"Initial load warning: {e}")
            # Continue anyway if page partially loaded

        # Wait for animations to initialize
        await asyncio.sleep(3.0)
        print("Page loaded successfully")

    async def smooth_scroll_to(self, target_y: int, duration: float = 2.0):
        """
        Perform smooth eased scrolling to a target position.
        Uses easeInOutCubic for natural motion.
        """
        current_y = await self.page.evaluate("window.scrollY")
        distance = target_y - current_y

        if abs(distance) < 10:
            return

        steps = int(duration * 60)  # 60fps

        for step in range(steps + 1):
            progress = step / steps
            # easeInOutCubic easing function
            if progress < 0.5:
                eased = 4 * progress * progress * progress
            else:
                eased = 1 - pow(-2 * progress + 2, 3) / 2

            scroll_y = current_y + (distance * eased)
            await self.page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await asyncio.sleep(1/60)  # ~60fps

    async def pause_with_subtle_motion(self, duration: float):
        """
        Pause at a section with subtle micro-movements for visual interest.
        """
        # Small oscillating movements to keep the video feeling alive
        start_y = await self.page.evaluate("window.scrollY")
        oscillations = int(duration * 2)  # 2 oscillations per second

        for i in range(oscillations):
            # Subtle up-down motion (±3 pixels)
            offset = 3 * math.sin(i * math.pi)
            await self.page.evaluate(f"window.scrollTo(0, {start_y + offset})")
            await asyncio.sleep(duration / oscillations)

        # Return to exact position
        await self.page.evaluate(f"window.scrollTo(0, {start_y})")

    async def interact_with_faq(self):
        """Open and close FAQ accordions for visual interest."""
        print("Interacting with FAQ section...")

        # Click first FAQ item
        try:
            faq_buttons = await self.page.query_selector_all('button[class*="cursor-pointer"]')
            if len(faq_buttons) >= 3:
                await faq_buttons[0].click()
                await asyncio.sleep(1.5)
                await faq_buttons[0].click()
                await asyncio.sleep(0.5)

                await faq_buttons[1].click()
                await asyncio.sleep(1.5)
                await faq_buttons[1].click()
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"FAQ interaction skipped: {e}")

    async def hover_pricing_cards(self):
        """Hover over pricing cards to trigger hover effects."""
        print("Hovering pricing cards...")

        try:
            # Find pricing card containers
            cards = await self.page.query_selector_all('[class*="pricing"], [class*="card"]')
            for card in cards[:3]:  # First 3 pricing cards
                await card.hover()
                await asyncio.sleep(0.8)
        except Exception as e:
            print(f"Pricing hover skipped: {e}")

    async def run_demo(self):
        """Execute the full demo recording sequence."""
        print("\n" + "="*60)
        print("TCG ELEVATE LANDING PAGE DEMO")
        print("="*60 + "\n")

        await self.setup()
        await self.navigate()

        # Initial pause at hero
        print(f"Starting demo at hero section...")
        await asyncio.sleep(3.0)

        # Scroll through each waypoint
        for i, waypoint in enumerate(self.waypoints):
            print(f"\n[{i+1}/{len(self.waypoints)}] {waypoint['name']}: {waypoint['description']}")

            # Smooth scroll to position using waypoint-specific duration
            scroll_duration = waypoint.get('scroll_duration', 2.0)
            await self.smooth_scroll_to(waypoint['position'], duration=scroll_duration)

            # Pause to let animations play and viewer absorb content
            await self.pause_with_subtle_motion(waypoint['pause'])

            # Special interactions at certain sections
            if waypoint['name'] == 'faq':
                await self.interact_with_faq()
            elif waypoint['name'] == 'pricing':
                await self.hover_pricing_cards()

        # Final sweep - scroll back to top slowly
        print("\n Returning to top...")
        await self.smooth_scroll_to(0, duration=4.0)
        await asyncio.sleep(2.0)

        print("\n" + "="*60)
        print("DEMO COMPLETE")
        print("="*60)

        await self.cleanup()

    async def cleanup(self):
        """Close browser and save recording."""
        if self.page:
            video_path = await self.page.video.path()
            print(f"\nRecording saved to: {video_path}")

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()


async def main():
    """Main entry point for the demo script."""
    demo = LandingPageDemo(
        url="https://pokemontcg.test/",
        output_dir="./recordings"
    )

    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
