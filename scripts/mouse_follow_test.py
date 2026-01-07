#!/usr/bin/env python3
"""
Mouse Following Test Demo

Records a demo where the mouse MOVES during the zoom period,
so we can actually see the mouse-following pan effect.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MouseFollowDemo:
    def __init__(self):
        self.output_dir = Path("./recordings")
        self.output_dir.mkdir(exist_ok=True)
        self.viewport = {"width": 1280, "height": 800}
        self.mouse_x = self.viewport["width"] // 2
        self.mouse_y = self.viewport["height"] // 2
        self.events = []
        self.mouse_path = []
        self.recording_start_time = 0
        self._tracking_active = False

    async def setup(self):
        logger.info("Initializing browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_dir = self.output_dir / f"mouse_follow_test_{timestamp}"

        self.context = await self.browser.new_context(
            viewport=self.viewport,
            record_video_dir=str(self.video_dir),
            record_video_size=self.viewport,
        )
        self.page = await self.context.new_page()
        await self._inject_cursor()
        logger.info(f"Recording to: {self.video_dir}")

    async def _inject_cursor(self):
        """Inject LARGE visible cursor so we can see it clearly."""
        await self.page.add_init_script("""
            const cursor = document.createElement('div');
            cursor.id = 'demo-cursor';
            // Large red cursor for visibility
            cursor.innerHTML = `
                <svg width="40" height="40" viewBox="0 0 40 40">
                    <circle cx="20" cy="20" r="15" fill="red" opacity="0.5"/>
                    <circle cx="20" cy="20" r="8" fill="red"/>
                    <path d="M8 4L8 34L17 24.5H25L8 4Z" fill="black" stroke="white" stroke-width="2"/>
                </svg>
            `;
            cursor.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;transform:translate(-8px,-4px);';
            document.addEventListener('DOMContentLoaded', () => document.body.appendChild(cursor));
            if (document.body) document.body.appendChild(cursor);
            window.updateCursor = (x, y) => {
                const c = document.getElementById('demo-cursor');
                if(c) { c.style.left=x+'px'; c.style.top=y+'px'; }
            };
        """)

    async def _ensure_cursor(self):
        await self.page.evaluate("""() => {
            if (!document.getElementById('demo-cursor')) {
                const c = document.createElement('div');
                c.id = 'demo-cursor';
                c.innerHTML = '<svg width="40" height="40" viewBox="0 0 40 40"><circle cx="20" cy="20" r="15" fill="red" opacity="0.5"/><circle cx="20" cy="20" r="8" fill="red"/><path d="M8 4L8 34L17 24.5H25L8 4Z" fill="black" stroke="white" stroke-width="2"/></svg>';
                c.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;transform:translate(-8px,-4px);';
                document.body.appendChild(c);
                window.updateCursor = (x,y) => { c.style.left=x+'px'; c.style.top=y+'px'; };
            }
        }""")

    async def _track_mouse_position(self):
        """Track mouse at 30fps."""
        while self._tracking_active:
            ts = time.time() - self.recording_start_time
            self.mouse_path.append({
                "t": round(ts, 3),
                "x": int(self.mouse_x),
                "y": int(self.mouse_y)
            })
            await asyncio.sleep(1/30)

    def log_event(self, event_type: str, x: int, y: int, label: str):
        ts = time.time() - self.recording_start_time
        self.events.append({
            "type": event_type,
            "timestamp": round(ts, 3),
            "x": x,
            "y": y,
            "label": label
        })
        logger.info(f"Event: {event_type} '{label}' at ({x}, {y}) @ {ts:.2f}s")

    async def move_to(self, x: int, y: int, duration: float = 0.5):
        """Smooth mouse movement."""
        await self._ensure_cursor()
        start_x, start_y = self.mouse_x, self.mouse_y
        steps = int(duration * 60)

        for i in range(steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)  # Smoothstep
            cx = start_x + (x - start_x) * t
            cy = start_y + (y - start_y) * t
            await self.page.evaluate(f"window.updateCursor && window.updateCursor({cx}, {cy})")
            await self.page.mouse.move(cx, cy)
            self.mouse_x, self.mouse_y = cx, cy
            await asyncio.sleep(1/60)

        self.mouse_x, self.mouse_y = x, y

    async def click_at(self, x: int, y: int, label: str):
        await self.move_to(x, y, duration=0.3)
        await asyncio.sleep(0.1)
        self.log_event("click", int(x), int(y), label)
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.1)

    async def run(self):
        await self.setup()

        # Navigate to Stripe
        await self.page.goto("https://stripe.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await self._ensure_cursor()

        # Start recording
        self.recording_start_time = time.time()
        self._tracking_active = True
        asyncio.create_task(self._track_mouse_position())
        logger.info("Started mouse tracking at ~30fps")
        self.log_event("start", 0, 0, "recording_start")

        # Initial position - CENTER of screen (not edge)
        await self.move_to(640, 400, duration=0.3)
        await asyncio.sleep(0.5)

        # Click in the CENTER of the page (not corner!)
        # This lets us see the zoom centering properly
        await self.click_at(640, 400, "Center Click")

        # NOW MOVE THE MOUSE while we're zoomed
        # This is what "mouse following" should track!
        await asyncio.sleep(0.2)  # Small pause after click

        # Move in a circle while zoomed
        logger.info("Moving mouse during zoom period...")
        center_x, center_y = 640, 400
        radius = 150
        for angle in range(0, 360, 15):
            import math
            x = center_x + radius * math.cos(math.radians(angle))
            y = center_y + radius * math.sin(math.radians(angle))
            await self.move_to(x, y, duration=0.08)

        await asyncio.sleep(0.3)

        # Second click - also in middle area
        await self.click_at(500, 350, "Second Click")

        # Move mouse again during this zoom
        await asyncio.sleep(0.2)
        await self.move_to(700, 350, duration=0.4)
        await self.move_to(700, 450, duration=0.3)
        await self.move_to(500, 450, duration=0.4)

        await asyncio.sleep(0.5)

        # End recording
        self.log_event("end", 0, 0, "recording_end")
        self._tracking_active = False
        await asyncio.sleep(0.3)

        logger.info(f"Stopped mouse tracking - {len(self.mouse_path)} positions recorded")

        # Save and cleanup
        await self.page.close()
        await self.context.close()

        # Export events
        events_file = self.video_dir / "events.json"
        with open(events_file, "w") as f:
            json.dump({
                "viewport": self.viewport,
                "url": "https://stripe.com",
                "events": self.events,
                "mouse_path": self.mouse_path,
            }, f, indent=2)

        logger.info("=" * 50)
        logger.info("RECORDING COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Events: {events_file}")
        logger.info(f"Mouse positions: {len(self.mouse_path)}")
        logger.info("")
        logger.info("This demo has MOUSE MOVEMENT during zoom!")
        logger.info("Run apply_zoom_effects.py to see mouse following")

        await self.browser.close()


async def main():
    demo = MouseFollowDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
