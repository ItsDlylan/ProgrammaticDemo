#!/usr/bin/env python3
"""
Stripe Landing Page Demo - Clean Recording

Records a clean demo with normal mouse cursor.
Exports click events as JSON for post-processing flexibility.

Raw video + click metadata = unlimited post-production options:
- Add zoom effects
- Add click highlights
- Add transitions
- Create multiple versions
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class StripeLandingDemo:
    """Clean demo recorder with click event tracking."""

    def __init__(self, url: str = "https://stripe.com", output_dir: str = "./recordings"):
        self.url = url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.viewport = {"width": 1280, "height": 800}
        self.mouse_x = self.viewport["width"] // 2
        self.mouse_y = self.viewport["height"] // 2

        # Event tracking for post-processing
        self.events = []
        self.recording_start_time = 0

        # Continuous mouse position tracking for smooth zoom effects
        self.mouse_path = []
        self._tracking_active = False
        self._tracking_task = None

    async def setup(self):
        """Initialize browser."""
        logger.info("Initializing browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_dir = self.output_dir / f"stripe_demo_{timestamp}"

        self.context = await self.browser.new_context(
            viewport=self.viewport,
            record_video_dir=str(self.video_dir),
            record_video_size=self.viewport,
        )
        self.page = await self.context.new_page()
        await self._inject_cursor()
        logger.info(f"Recording to: {self.video_dir}")

    async def _inject_cursor(self):
        """Inject normal mouse cursor."""
        await self.page.add_init_script("""
            const cursor = document.createElement('div');
            cursor.id = 'demo-cursor';
            cursor.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20"><path d="M4 2L4 17L8.5 12.5H12.5L4 2Z" fill="black" stroke="white" stroke-width="1.2"/></svg>';
            cursor.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;filter:drop-shadow(1px 1px 1px rgba(0,0,0,0.3));';
            document.addEventListener('DOMContentLoaded', () => document.body.appendChild(cursor));
            if (document.body) document.body.appendChild(cursor);
            window.updateCursor = (x, y) => { const c = document.getElementById('demo-cursor'); if(c) { c.style.left=x+'px'; c.style.top=y+'px'; }};
        """)

    async def _ensure_cursor(self):
        """Ensure cursor exists."""
        await self.page.evaluate("""() => {
            if (!document.getElementById('demo-cursor')) {
                const c = document.createElement('div');
                c.id = 'demo-cursor';
                c.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20"><path d="M4 2L4 17L8.5 12.5H12.5L4 2Z" fill="black" stroke="white" stroke-width="1.2"/></svg>';
                c.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;filter:drop-shadow(1px 1px 1px rgba(0,0,0,0.3));';
                document.body.appendChild(c);
                window.updateCursor = (x,y) => { c.style.left=x+'px'; c.style.top=y+'px'; };
            }
        }""")

    async def _track_mouse_position(self):
        """Background task to track mouse position at ~30fps for smooth zoom effects."""
        while self._tracking_active:
            ts = time.time() - self.recording_start_time
            self.mouse_path.append({
                "t": round(ts, 3),
                "x": int(self.mouse_x),
                "y": int(self.mouse_y)
            })
            await asyncio.sleep(0.033)  # ~30fps (every 33ms)

    def _start_mouse_tracking(self):
        """Start continuous mouse position tracking."""
        self._tracking_active = True
        self._tracking_task = asyncio.create_task(self._track_mouse_position())
        logger.info("Started continuous mouse tracking at ~30fps")

    async def _stop_mouse_tracking(self):
        """Stop continuous mouse position tracking."""
        self._tracking_active = False
        if self._tracking_task:
            await self._tracking_task
            self._tracking_task = None
        logger.info(f"Stopped mouse tracking - {len(self.mouse_path)} positions recorded")

    def log_event(self, event_type: str, x: int, y: int, label: str = ""):
        """Log event for post-processing."""
        ts = time.time() - self.recording_start_time
        self.events.append({
            "type": event_type,
            "timestamp": round(ts, 3),
            "x": x,
            "y": y,
            "label": label
        })
        logger.info(f"Event: {event_type} '{label}' at ({x}, {y}) @ {ts:.2f}s")

    async def move_to(self, x: int, y: int, duration: float = 0.6):
        """Smooth mouse movement."""
        await self._ensure_cursor()
        start_x, start_y = self.mouse_x, self.mouse_y
        steps = int(duration * 60)

        for step in range(steps + 1):
            t = step / steps
            t = t * t * (3 - 2 * t)  # Smoothstep
            cx = start_x + (x - start_x) * t
            cy = start_y + (y - start_y) * t
            await self.page.evaluate(f"window.updateCursor && window.updateCursor({cx}, {cy})")
            await self.page.mouse.move(cx, cy)
            await asyncio.sleep(1/60)

        self.mouse_x, self.mouse_y = x, y

    async def click_at(self, x: int, y: int, label: str):
        """Move to position and log click."""
        await self.move_to(x, y)
        await asyncio.sleep(0.2)
        self.log_event("click", x, y, label)
        await asyncio.sleep(0.3)

    async def scroll_to(self, y: float, duration: float = 1.0):
        """Smooth scroll."""
        current = await self.page.evaluate("window.scrollY")
        steps = int(duration * 60)
        for step in range(steps + 1):
            t = step / steps
            t = t * t * (3 - 2 * t)
            await self.page.evaluate(f"window.scrollTo(0, {current + (y - current) * t})")
            await asyncio.sleep(1/60)

    async def run_demo(self):
        """Record the demo."""
        logger.info("="*50)
        logger.info("STRIPE DEMO - Clean Recording")
        logger.info("="*50)

        await self.setup()
        await self.page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2.0)
        await self._ensure_cursor()

        # Start timing and mouse tracking
        self.recording_start_time = time.time()
        self._start_mouse_tracking()
        self.log_event("start", 0, 0, "recording_start")

        # Move cursor into view
        await self.move_to(640, 300, duration=0.8)
        await asyncio.sleep(0.5)

        # Find and click Sign In link
        logger.info("\n>>> Sign In link")
        sign_in = await self.page.query_selector('a[href*="dashboard.stripe.com/login"]')
        if sign_in:
            box = await sign_in.bounding_box()
            if box:
                await self.click_at(int(box["x"] + box["width"]/2), int(box["y"] + box["height"]/2), "Sign In")

        await asyncio.sleep(0.3)

        # Find and click Contact Sales button
        logger.info("\n>>> Contact Sales button")
        contact = await self.page.query_selector('a[href*="contact/sales"]')
        if contact:
            box = await contact.bounding_box()
            if box:
                await self.click_at(int(box["x"] + box["width"]/2), int(box["y"] + box["height"]/2), "Contact Sales")

        await asyncio.sleep(0.3)

        # Quick scroll
        await self.move_to(640, 400, duration=0.3)
        self.log_event("scroll_start", 640, 400, "scroll_down")
        await self.scroll_to(600, duration=1.0)
        self.log_event("scroll_end", 640, 400, "scroll_down")
        await asyncio.sleep(0.5)

        await self.scroll_to(0, duration=0.8)
        await asyncio.sleep(0.5)

        self.log_event("end", 0, 0, "recording_end")

        # Stop mouse tracking
        await self._stop_mouse_tracking()

        # Cleanup and save
        video_path = None
        if self.page:
            video_path = await self.page.video.path()
        await self.context.close()
        await self.browser.close()

        # Save events JSON with mouse path for smooth zoom effects
        events_file = self.video_dir / "events.json"
        with open(events_file, "w") as f:
            json.dump({
                "viewport": self.viewport,
                "url": self.url,
                "events": self.events,
                "mouse_path": self.mouse_path
            }, f, indent=2)

        logger.info("\n" + "="*50)
        logger.info("RECORDING COMPLETE")
        logger.info("="*50)
        logger.info(f"Video: {video_path}")
        logger.info(f"Events: {events_file}")
        logger.info(f"\nClick events recorded: {len([e for e in self.events if e['type'] == 'click'])}")
        logger.info(f"Mouse positions tracked: {len(self.mouse_path)} (~30fps)")
        logger.info("\nPost-process with FFmpeg using events.json for:")
        logger.info("  - Smooth animated zoom effects")
        logger.info("  - Mouse-following pan during zoom")
        logger.info("  - Click ripple animations")
        logger.info("  - Multiple effect variations")


async def main():
    demo = StripeLandingDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
