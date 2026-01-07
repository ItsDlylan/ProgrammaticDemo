"""INT-009: Test click effect rendering.

This test verifies that:
1. Click effects can be enabled and configured
2. Ripple animation frames are generated
3. Effect filter chain is built for video rendering
4. Effects are properly added to the compositor
"""

import pytest

from programmatic_demo.effects.click_effect import (
    ClickEffect,
    ClickEffectConfig,
    RippleFrame,
    create_click_effect,
)
from programmatic_demo.effects.compositor import (
    Compositor,
    Effect,
    EffectConfig,
    EffectEvent,
    EffectType,
    EventQueue,
)


class TestClickEffectConfig:
    """Test click effect configuration."""

    def test_default_config(self):
        """Test default click effect configuration."""
        config = ClickEffectConfig()

        assert config.radius == 30
        assert config.duration_ms == 300
        assert config.color == "#FF5722"
        assert config.opacity == 0.7
        assert config.style == "ripple"

    def test_custom_config(self):
        """Test custom click effect configuration."""
        config = ClickEffectConfig(
            radius=50,
            duration_ms=500,
            color="#00FF00",
            opacity=0.5,
            style="highlight",
        )

        assert config.radius == 50
        assert config.duration_ms == 500
        assert config.color == "#00FF00"
        assert config.opacity == 0.5
        assert config.style == "highlight"


class TestRippleGeneration:
    """Test ripple animation frame generation."""

    def test_generate_ripple_frames(self):
        """Test that ripple frames are generated."""
        effect = ClickEffect()
        frames = effect.generate_ripple(100, 200)

        assert len(frames) > 0
        assert all(isinstance(f, RippleFrame) for f in frames)

    def test_ripple_frames_have_correct_position(self):
        """Test that ripple frames have correct center position."""
        effect = ClickEffect()
        frames = effect.generate_ripple(100, 200)

        for frame in frames:
            assert frame.x == 100
            assert frame.y == 200

    def test_ripple_radius_expands(self):
        """Test that ripple radius expands over time."""
        effect = ClickEffect()
        frames = effect.generate_ripple(100, 200)

        # First frame should have small/no radius
        assert frames[0].radius < frames[-1].radius

        # Last frame should be at max radius
        assert frames[-1].radius == pytest.approx(effect.config.radius, rel=0.1)

    def test_ripple_opacity_fades(self):
        """Test that ripple opacity fades over time."""
        effect = ClickEffect()
        frames = effect.generate_ripple(100, 200)

        # First frame should have high opacity
        assert frames[0].opacity > frames[-1].opacity

        # Last frame should have very low opacity
        assert frames[-1].opacity < 0.1

    def test_ripple_timestamp_progression(self):
        """Test that ripple timestamps progress correctly."""
        config = ClickEffectConfig(duration_ms=300)
        effect = ClickEffect(config)
        frames = effect.generate_ripple(100, 200, start_time_ms=1000)

        # First frame at start time
        assert frames[0].timestamp_ms == 1000

        # Last frame at start + duration
        assert frames[-1].timestamp_ms == pytest.approx(1300, rel=0.1)


class TestClickEffectHighlight:
    """Test static highlight effect generation."""

    def test_generate_highlight(self):
        """Test highlight effect generation."""
        effect = ClickEffect()
        highlight = effect.generate_highlight(100, 200)

        assert highlight["type"] == "highlight"
        assert highlight["x"] == 100
        assert highlight["y"] == 200
        assert highlight["radius"] == effect.config.radius
        assert highlight["color"] == effect.config.color

    def test_highlight_custom_duration(self):
        """Test highlight with custom duration."""
        effect = ClickEffect()
        highlight = effect.generate_highlight(100, 200, duration_ms=1000)

        assert highlight["duration_ms"] == 1000


class TestClickEffectPulse:
    """Test pulse animation generation."""

    def test_generate_pulse(self):
        """Test pulse animation generates multiple ripples."""
        effect = ClickEffect()
        frames = effect.generate_pulse(100, 200, pulses=2)

        # Should have frames from 2 ripples
        assert len(frames) > len(effect.generate_ripple(100, 200))

    def test_pulse_multiple_ripples(self):
        """Test pulse creates the correct number of ripples."""
        config = ClickEffectConfig(duration_ms=300)
        effect = ClickEffect(config)

        single_ripple_count = len(effect.generate_ripple(100, 200))
        pulse_frames = effect.generate_pulse(100, 200, pulses=3)

        # Should have approximately 3x the frames
        assert len(pulse_frames) >= single_ripple_count * 2


class TestCreateClickEffectConvenience:
    """Test the convenience function for creating click effects."""

    def test_create_click_effect(self):
        """Test convenience function creates ripple frames."""
        frames = create_click_effect(100, 200)

        assert len(frames) > 0
        assert all(isinstance(f, RippleFrame) for f in frames)

    def test_create_click_effect_with_config(self):
        """Test convenience function with custom config."""
        config = ClickEffectConfig(radius=50)
        frames = create_click_effect(100, 200, config=config)

        assert frames[-1].radius == pytest.approx(50, rel=0.1)


class TestCompositorClickEffects:
    """Test click effects integration with Compositor."""

    def test_add_ripple_event_to_compositor(self):
        """Test adding a ripple event to the compositor."""
        compositor = Compositor()

        config = EffectConfig(
            type=EffectType.RIPPLE,
            params={"radius": 30, "color": "FF5722"},
            duration_ms=300,
        )

        event = EffectEvent(
            type=EffectType.RIPPLE,
            timestamp_ms=1000,
            position=(100, 200),
            config=config,
        )

        compositor.event_queue.add_event(event)

        assert len(compositor.event_queue) == 1

    def test_build_filter_chain_with_ripple(self):
        """Test building FFmpeg filter chain with ripple effect."""
        compositor = Compositor()

        config = EffectConfig(
            type=EffectType.RIPPLE,
            params={"radius": 30, "color": "FF5722"},
            duration_ms=300,
        )

        event = EffectEvent(
            type=EffectType.RIPPLE,
            timestamp_ms=1000,
            position=(100, 200),
            config=config,
        )

        compositor.event_queue.add_event(event)
        filter_chain = compositor.build_filter_chain()

        assert filter_chain != ""
        assert "drawbox" in filter_chain
        assert "enable" in filter_chain

    def test_multiple_click_effects_in_sequence(self):
        """Test multiple click effects at different times."""
        compositor = Compositor()

        # Add multiple ripple events
        for i, ts in enumerate([1000, 2000, 3000]):
            config = EffectConfig(
                type=EffectType.RIPPLE,
                params={"radius": 30},
                duration_ms=300,
            )
            event = EffectEvent(
                type=EffectType.RIPPLE,
                timestamp_ms=ts,
                position=(100 + i * 50, 200),
                config=config,
            )
            compositor.event_queue.add_event(event)

        assert len(compositor.event_queue) == 3

        filter_chain = compositor.build_filter_chain()
        # Should have multiple drawbox filters
        assert filter_chain.count("drawbox") == 3

    def test_effect_summary_includes_ripple(self):
        """Test effect summary includes ripple effects."""
        compositor = Compositor()

        config = EffectConfig(type=EffectType.RIPPLE)
        event = EffectEvent(
            type=EffectType.RIPPLE,
            timestamp_ms=1000,
            position=(100, 200),
            config=config,
        )
        compositor.event_queue.add_event(event)

        summary = compositor.get_effect_summary()

        assert summary["total_events"] == 1
        assert "ripple" in summary["event_types"]
        assert summary["event_types"]["ripple"] == 1


class TestEventQueue:
    """Test the EventQueue functionality for click effects."""

    def test_events_sorted_by_timestamp(self):
        """Test that events are sorted by timestamp."""
        queue = EventQueue()

        # Add events out of order
        for ts in [3000, 1000, 2000]:
            event = EffectEvent(
                type=EffectType.RIPPLE,
                timestamp_ms=ts,
                position=(100, 200),
            )
            queue.add_event(event)

        # Should be in order
        events = queue.events
        assert events[0].timestamp_ms == 1000
        assert events[1].timestamp_ms == 2000
        assert events[2].timestamp_ms == 3000

    def test_get_events_in_range(self):
        """Test getting events within a time range."""
        queue = EventQueue()

        for ts in [1000, 2000, 3000, 4000, 5000]:
            event = EffectEvent(
                type=EffectType.RIPPLE,
                timestamp_ms=ts,
                position=(100, 200),
            )
            queue.add_event(event)

        events = queue.get_events_in_range(2000, 4000)

        assert len(events) == 3
        assert all(2000 <= e.timestamp_ms <= 4000 for e in events)

    def test_get_active_events(self):
        """Test getting active events at a timestamp."""
        queue = EventQueue()

        config = EffectConfig(type=EffectType.RIPPLE, duration_ms=500)
        event = EffectEvent(
            type=EffectType.RIPPLE,
            timestamp_ms=1000,
            position=(100, 200),
            config=config,
        )
        queue.add_event(event)

        # During effect
        active = queue.get_active_events(1200)
        assert len(active) == 1

        # After effect
        active = queue.get_active_events(2000)
        assert len(active) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
