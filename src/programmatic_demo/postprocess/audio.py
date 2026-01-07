"""Audio processing for demo videos.

This module provides audio capabilities:
- Background music mixing
- Sound effect triggers
- Volume adjustment
- Audio normalization
"""

from dataclasses import dataclass, field
from typing import Any

from programmatic_demo.postprocess.editor import FFmpegBuilder


@dataclass
class AudioTrack:
    """An audio track to add to the video.

    Attributes:
        path: Path to audio file.
        start_time: Start time in the video (seconds).
        end_time: End time (None for full duration).
        volume: Volume level (0.0-1.0, 1.0 = original).
        fade_in_ms: Fade in duration in milliseconds.
        fade_out_ms: Fade out duration in milliseconds.
        loop: Whether to loop the audio.
    """

    path: str
    start_time: float = 0.0
    end_time: float | None = None
    volume: float = 1.0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    loop: bool = False


@dataclass
class SoundEffect:
    """A sound effect to play at a specific time.

    Attributes:
        path: Path to sound effect file.
        trigger_time: Time to play the effect (seconds).
        volume: Volume level (0.0-1.0).
    """

    path: str
    trigger_time: float
    volume: float = 1.0


@dataclass
class VoiceoverSegment:
    """A voiceover segment at a specific timestamp.

    Attributes:
        path: Path to voiceover audio file.
        start_time: Start time in video (seconds).
        end_time: End time (None to use audio duration).
        volume: Voiceover volume (0.0-1.0).
        duck_background: Whether to reduce background audio volume.
        duck_level: Background audio level during voiceover (0.0-1.0).
    """

    path: str
    start_time: float
    end_time: float | None = None
    volume: float = 1.0
    duck_background: bool = True
    duck_level: float = 0.2


class AudioManager:
    """Manages audio for demo videos.

    Provides methods to add background music, sound effects,
    and adjust audio levels.
    """

    def __init__(self) -> None:
        """Initialize the AudioManager."""
        self._tracks: list[AudioTrack] = []
        self._effects: list[SoundEffect] = []
        self._voiceovers: list[VoiceoverSegment] = []
        self._master_volume: float = 1.0

    @property
    def tracks(self) -> list[AudioTrack]:
        """Get all audio tracks."""
        return self._tracks.copy()

    @property
    def effects(self) -> list[SoundEffect]:
        """Get all sound effects."""
        return self._effects.copy()

    @property
    def voiceovers(self) -> list[VoiceoverSegment]:
        """Get all voiceover segments."""
        return self._voiceovers.copy()

    def add_background_music(
        self,
        path: str,
        volume: float = 0.3,
        fade_in_ms: int = 2000,
        fade_out_ms: int = 2000,
        loop: bool = True,
    ) -> AudioTrack:
        """Add background music track.

        Args:
            path: Path to music file.
            volume: Music volume (default 0.3 for background).
            fade_in_ms: Fade in duration.
            fade_out_ms: Fade out duration.
            loop: Whether to loop the music.

        Returns:
            The created AudioTrack.
        """
        track = AudioTrack(
            path=path,
            volume=volume,
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
            loop=loop,
        )
        self._tracks.append(track)
        return track

    def add_narration(
        self,
        path: str,
        start_time: float = 0.0,
        volume: float = 1.0,
    ) -> AudioTrack:
        """Add a narration track.

        Args:
            path: Path to narration audio file.
            start_time: When to start the narration.
            volume: Narration volume.

        Returns:
            The created AudioTrack.
        """
        track = AudioTrack(
            path=path,
            start_time=start_time,
            volume=volume,
        )
        self._tracks.append(track)
        return track

    def add_sound_effect(
        self,
        path: str,
        trigger_time: float,
        volume: float = 1.0,
    ) -> SoundEffect:
        """Add a sound effect at a specific time.

        Args:
            path: Path to sound effect file.
            trigger_time: Time to play the effect.
            volume: Effect volume.

        Returns:
            The created SoundEffect.
        """
        effect = SoundEffect(
            path=path,
            trigger_time=trigger_time,
            volume=volume,
        )
        self._effects.append(effect)
        return effect

    def add_click_sound(
        self,
        trigger_time: float,
        sound_path: str | None = None,
    ) -> SoundEffect:
        """Add a click sound effect.

        Args:
            trigger_time: Time of the click.
            sound_path: Custom click sound path.

        Returns:
            The created SoundEffect.
        """
        # Default to a placeholder path if not provided
        path = sound_path or "sounds/click.wav"
        return self.add_sound_effect(path, trigger_time, volume=0.5)

    def add_typing_sound(
        self,
        start_time: float,
        duration: float,
        sound_path: str | None = None,
    ) -> AudioTrack:
        """Add typing sound effect for a duration.

        Args:
            start_time: Start time of typing.
            duration: Duration of typing.
            sound_path: Custom typing sound path.

        Returns:
            The created AudioTrack.
        """
        path = sound_path or "sounds/typing.wav"
        track = AudioTrack(
            path=path,
            start_time=start_time,
            end_time=start_time + duration,
            volume=0.3,
            loop=True,
        )
        self._tracks.append(track)
        return track

    def add_voiceover(
        self,
        video_path: str,
        audio_path: str,
        timestamps: list[tuple[float, float | None]] | None = None,
        output_path: str | None = None,
        volume: float = 1.0,
        duck_background: bool = True,
        duck_level: float = 0.2,
    ) -> dict[str, Any]:
        """Add voiceover audio to a video with optional background audio ducking.

        Args:
            video_path: Path to input video file.
            audio_path: Path to voiceover audio file.
            timestamps: List of (start_time, end_time) tuples for segments.
                       If None, voiceover plays from beginning.
            output_path: Path for output video (defaults to video_path with suffix).
            volume: Voiceover volume (0.0-1.0).
            duck_background: Whether to reduce background audio during voiceover.
            duck_level: Background volume during voiceover (0.0-1.0).

        Returns:
            Result dict with success status and output path.
        """
        # Create voiceover segments
        if timestamps:
            for start, end in timestamps:
                segment = VoiceoverSegment(
                    path=audio_path,
                    start_time=start,
                    end_time=end,
                    volume=volume,
                    duck_background=duck_background,
                    duck_level=duck_level,
                )
                self._voiceovers.append(segment)
        else:
            # Single segment from start
            segment = VoiceoverSegment(
                path=audio_path,
                start_time=0.0,
                end_time=None,
                volume=volume,
                duck_background=duck_background,
                duck_level=duck_level,
            )
            self._voiceovers.append(segment)

        # Generate output path if not provided
        if output_path is None:
            import os
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_voiceover{ext}"

        # Build FFmpeg command
        builder = FFmpegBuilder().overwrite().input(video_path).input(audio_path)

        # Build filter complex for mixing audio
        # [0:a] is original video audio, [1:a] is voiceover
        filters = []

        if duck_background and self._voiceovers:
            # Apply sidechaincompress to duck background during voiceover
            # or use volume automation
            # Simple approach: reduce original audio volume, mix with voiceover
            filters.append(f"[0:a]volume={duck_level}[bg]")
            filters.append(f"[1:a]volume={volume}[vo]")
            filters.append("[bg][vo]amix=inputs=2:duration=longest[aout]")
            audio_filter = ";".join(filters)
            builder = (
                builder
                .filter(audio_filter, filter_type="complex")
                .output(output_path, **{"map": "0:v", "map": "[aout]", "c:v": "copy"})
            )
        else:
            # Simple mix without ducking
            filters.append(f"[0:a][1:a]amix=inputs=2:duration=longest[aout]")
            audio_filter = filters[0]
            builder = (
                builder
                .filter(audio_filter, filter_type="complex")
                .output(output_path, **{"map": "0:v", "map": "[aout]", "c:v": "copy"})
            )

        try:
            builder.run()
            return {
                "success": True,
                "output": output_path,
                "segments": len(self._voiceovers),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def set_master_volume(self, volume: float) -> None:
        """Set the master volume level.

        Args:
            volume: Master volume (0.0-1.0).
        """
        self._master_volume = max(0.0, min(1.0, volume))

    def normalize_audio(
        self,
        input_path: str,
        output_path: str,
        target_level: float = -14.0,
    ) -> dict[str, Any]:
        """Normalize audio levels in a video.

        Args:
            input_path: Input video path.
            output_path: Output video path.
            target_level: Target loudness in LUFS.

        Returns:
            Result dict with success status.
        """
        builder = (
            FFmpegBuilder()
            .overwrite()
            .input(input_path)
            .filter(f"loudnorm=I={target_level}")
            .output(output_path)
        )

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def adjust_volume(
        self,
        input_path: str,
        output_path: str,
        volume: float = 1.0,
    ) -> dict[str, Any]:
        """Adjust volume of a video.

        Args:
            input_path: Input video path.
            output_path: Output video path.
            volume: Volume multiplier.

        Returns:
            Result dict with success status.
        """
        builder = (
            FFmpegBuilder()
            .overwrite()
            .input(input_path)
            .output(output_path, **{"af": f"volume={volume}"})
        )

        try:
            builder.run()
            return {"success": True, "output": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear(self) -> None:
        """Clear all audio tracks, effects, and voiceovers."""
        self._tracks.clear()
        self._effects.clear()
        self._voiceovers.clear()

    def to_ffmpeg_filter(self) -> str:
        """Generate FFmpeg filter for mixing all audio.

        Returns:
            FFmpeg audio filter string.
        """
        filters = []

        for i, track in enumerate(self._tracks):
            volume = track.volume * self._master_volume
            filter_parts = [f"[{i}:a]volume={volume}"]

            if track.fade_in_ms > 0:
                filter_parts.append(f"afade=t=in:d={track.fade_in_ms/1000}")

            if track.fade_out_ms > 0:
                filter_parts.append(f"afade=t=out:d={track.fade_out_ms/1000}")

            filters.append(",".join(filter_parts) + f"[a{i}]")

        if len(filters) > 1:
            # Mix multiple tracks
            labels = "".join(f"[a{i}]" for i in range(len(filters)))
            filters.append(f"{labels}amix=inputs={len(filters)}")

        return ";".join(filters) if filters else ""


# Convenience functions
def add_background_music(
    path: str,
    volume: float = 0.3,
) -> AudioTrack:
    """Convenience function to add background music.

    Args:
        path: Path to music file.
        volume: Music volume.

    Returns:
        AudioTrack object.
    """
    manager = AudioManager()
    return manager.add_background_music(path, volume)


def add_click_sound(trigger_time: float) -> SoundEffect:
    """Convenience function to add a click sound.

    Args:
        trigger_time: Time to play the click.

    Returns:
        SoundEffect object.
    """
    manager = AudioManager()
    return manager.add_click_sound(trigger_time)
